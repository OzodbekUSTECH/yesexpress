import requests
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from django.utils import timezone
from django.db import transaction
from django.db.models.functions import Coalesce
from django.db.models import Q, Subquery, OuterRef, Count, IntegerField, Value

from rest_framework.exceptions import ValidationError

from .utils import notify
from .serializers import OrderSerializer

from user.models import User
from common.models import Settings
from courier.models import InstitutionDeliverySettings
from institution.models import InstitutionBranchSchedule
from .models import OrderItemGroup, OrderItem, Order, OrderStatusTimeline, TelegramMessage

from payme.utils import make_payment
from courier.services import get_delivery_settings
from institution.services import find_suitable_branch
from .distance_calculator import calculate_distance
from .promo_codes.services import PromoCodeService
from .push_notifications.services import send_notification_to_institution

def calculate_delivering_sum(
        institution, order_address, branch=None, global_delivery_settings=None
):
    if institution.free_delivery:
        return 0

    delivery_settings = InstitutionDeliverySettings.objects.filter(institution=institution).first()
    if not delivery_settings:
        delivery_settings = global_delivery_settings or get_delivery_settings()

    if not branch:
        branch = find_suitable_branch(institution, order_address)
    
    distance = calculate_distance(branch.address, order_address) if branch else 0
    
    if distance < delivery_settings.min_distance:
        return delivery_settings.min_delivery_price

    return round(
        delivery_settings.min_delivery_price + delivery_settings.price_per_km * distance, -2
    )

class OrderItemGroupService:
    def __init__(self, validated_data=None, order_service=None, instance=None):
        self.validated_data = validated_data
        self.order_service = order_service
        self.items = None
        self.instance = instance

    def create(self):
        self.items = list(self.validated_data.pop("items"))
        group = OrderItemGroup(**self.validated_data, order=self.order_service.instance)
        self.instance = group
        group.products_sum = self._calculate_products_sum()
        group.commission = self._calculate_commission()
        group.total_sum = group.products_sum + group.delivering_sum
        group.save()

        self._create_items()

        return group

    def _calculate_products_sum(self):
        products_sum = 0

        for item in self.items:
            options_sum = sum([option.adding_price for option in item["options"]])
            product_price = item["product"].price + options_sum
            products_sum += product_price * item["count"]

        return products_sum

    def _calculate_commission(self):
        institution = self.validated_data["institution"]
        order = self.instance.order

        if order.self_pickup:
            comission_percentage = institution.tax_percentage_self_pickup
            if comission_percentage is None:
                settings = Settings.load()
                comission_percentage = settings.common_percentage_self_pickup
        elif institution.delivery_by_own:
            comission_percentage = institution.tax_percentage_restaurant_couriers
            if comission_percentage is None:
                settings = Settings.load()
                comission_percentage = settings.common_percentage_restaurant_couriers
        else:
            comission_percentage = institution.tax_percentage_ordinary
            if comission_percentage is None:
                settings = Settings.load()
                comission_percentage = settings.common_percentage_ordinary

        comission = (self._calculate_products_sum() * comission_percentage) / 100
        return round(comission, -1)

    def _create_items(self) -> None:
        items = self.items
        for item in items:
            _item = OrderItem(
                order_item_group=self.instance,
                product=item["product"],
                count=item["count"],
                total_sum=item["product"].price * item["count"],
            )

            _item.total_sum += sum(
                [option.adding_price * _item.count for option in item["options"]]
            )
            _item.save()

            _options_through = [
                OrderItem.options.through(orderitem=_item, optionitem=_option)
                for _option in item["options"]
            ]
            OrderItem.options.through.objects.bulk_create(_options_through)

    def _send_order_data(self):
        channel_layer = get_channel_layer()
        group = self.instance.item_groups.first()
        async_to_sync(channel_layer.group_send)(
            f"institution_{self.instance.institution_id}",
            {
                "type": "order_data",
                "status": self.instance.status,
                "payment_type": self.instance.payment_method,
                "order_id": self.instance.id,
                "group_id": group.id,
                "courier": self.instance.courier.id if self.instance.courier else None,
                "products_sum": group.products_sum,
                "total_sum": group.total_sum,
                "preparing_time": self.instance.preparing_time,
                "institution_name": group.institution.name,
                "branch_name": group.institution_branch.name,
                "created_at": self.instance.created_at.strftime("%Y-%m-%d")

            }
        )
        
        async_to_sync(channel_layer.group_send)(
            f"order_{self.instance.id}",
            {
                "type": "order_by_id",
                "status": self.instance.status,
                "order_id": self.instance.id
            }
        )

def payme(order):
    if order.payment_method == "payme" and order.cdt and order.is_paid is False:
        
        products = []
        discount_remainder = order.discount_sum
        branch = order.item_groups.first().institution_branch
        items = order.item_groups.first().items.all()
        delivery_price = order.item_groups.first().delivering_sum 
        for i in items:
            product = i.product
            count = i.count
            adding_price = sum([option.adding_price for option in i.options.all()])
            product_price = product.price + adding_price
            product_amount = product_price * count
            discount_amount = 0

            if discount_remainder > 0:
                if discount_remainder - product_amount > 0:
                    discount_amount = product_amount * 100
                    discount_remainder = discount_remainder - product_amount
                elif discount_remainder - product_amount <= 0:
                    discount_amount = discount_remainder * 100
                    discount_remainder = discount_remainder - product_amount
            
            if not i.is_incident:
                products.append(
                    {
                        "title": product.name,
                        "price": product_price * 100,
                        "count": count,
                        "code": product.spic_id,
                        "package_code": product.package_code,
                        "vat_percent": product.vat,
                        "discount": discount_amount
                    }
                )
        if order.package_amount > 0:
            products.append(
                {
                    "title": "Пакет",
                    "price": order.package_amount * 100,
                    "count": order.package_quantity or 1,
                    "code": branch.package_spic_id,
                    "package_code": branch.package_code,
                    "vat_percent": branch.package_vat,
                    "discount": 0
                }
            )
        if delivery_price > 0:
            products.append(
                {
                    "title": "Служба доставки еды",
                    "price": delivery_price * 100,
                    "count": 1,
                    "code": "10112006004000000",
                    "package_code": "1202229",
                    "vat_percent": 0,
                    "discount": 0
                }
            )
        
        with requests.Session() as session:
            res = make_payment(session, order, order.cdt, products)
            print(products, res)
            return res
            
class OrderService:
    def __init__(self, serializer_instance: OrderSerializer, customer: User):
        self.serializer_instance = serializer_instance
        self.data = serializer_instance.initial_data
        self.validated_data = serializer_instance.validated_data
        self.delivery_settings = get_delivery_settings()
        self.customer = customer
        self.groups = None
        self.instance = None
        self.promo_code_service = None
        if promo_code := self.validated_data.pop("promo_code", None):
            self.promo_code_service = PromoCodeService(promo_code)

    def create(self):
        with transaction.atomic():
            self.groups = list(self.validated_data.pop("item_groups"))
            card = self.validated_data.pop("card")
            order = Order(**self.validated_data, is_paid=False, customer=self.customer)    
            self.instance = order

            if order.status == "pre-order":
                self._validate_preorder_time(order)

            order.status = "created"
            order.products_sum = self._calculate_products_sum()
            order.delivering_sum = 0

            for group in self.groups:
                institution = group["institution"]
                
                institution_branch = self.is_institution_available(order, institution)
                
                if not institution_branch:
                    raise Exception("Institution not available")

                group["delivering_sum"] = calculate_delivering_sum(
                    institution, order.address, institution_branch, self.delivery_settings
                )
                group["institution_branch"] = institution_branch
                order.delivering_sum += group["delivering_sum"]

            order.total_sum = self._calculate_total_sum_without_discounts()
            order.discount_sum = self._calculate_discount_sum()
            order.total_sum = self._calculate_total_sum()

            # self._validate_min_order_amount(order)

            if card:
                order.cdt = card.token
            order.package_amount = self.validated_data.get('package_amount', 0)
            order.package_quantity = self.validated_data.get('package_quantity', 0)
            order.save()

            OrderStatusTimeline.objects.get_or_create(order=order)
            TelegramMessage.objects.get_or_create(order=order)

            if self.promo_code_service:
                self.promo_code_service.use(self.customer, order)

            for group in self.groups:
                OrderItemGroupService(group, self).create()
            self._operator_add_with_order()
        
        send_notification_to_institution(order.id)
            
        notify(order)
        return order

    def _validate_min_order_amount(self, order):
        institution_branch = self.groups[0].get("institution_branch")
        if institution_branch:
            min_order_amount = institution_branch.min_order_amount
            
            if order.products_sum < min_order_amount:
                print(f"Минимальная сумма для предзаказа — {min_order_amount} сум. У вас — {order.products_sum} сум.")
                raise ValidationError(f"Минимальная сумма для предзаказа — {min_order_amount} сум. У вас — {order.products_sum} сум.")
    
    def _validate_preorder_time(self, order):
        delivery_time = order.delivery_time
        if not delivery_time:
            raise ValidationError("Для предзаказа необходимо указать время доставки.")

        institution_branch = self.groups[0].get("institution_branch")
        if not institution_branch:
            raise ValidationError("Не указан филиал заведения.")

        min_delivery_time = timezone.now() + timedelta(
            minutes=institution_branch.min_preorder_minutes
        )
        if delivery_time < min_delivery_time:
            raise ValidationError(
                f"Время доставки должно быть не раньше чем через {institution_branch.min_preorder_minutes} минут."
            )

        max_preorder_date = timezone.now() + timedelta(days=institution_branch.max_preorder_days)
        if delivery_time > max_preorder_date:
            raise ValidationError(
                f"Предзаказ возможен только на {institution_branch.max_preorder_days} дней вперед."
            )

        if not self._is_valid_delivery_time(delivery_time, institution_branch):
            raise ValidationError("Заведение не работает в указанное время.")

        if not self._is_valid_order_time(delivery_time, institution_branch):
            raise ValidationError("Общее время выполнения заказа превышает время работы заведения.")


    def _is_valid_delivery_time(self, delivery_time, institution_branch):
        day_of_week = delivery_time.strftime("%A").upper()
        delivery_time = delivery_time.time()

        schedule_entry = InstitutionBranchSchedule.objects.filter(
            institution=institution_branch,
            day_of_week=day_of_week,
            is_active=True,
            start_time__lte=delivery_time,
            end_time__gte=delivery_time,
        ).exists()

        return schedule_entry

    def _is_valid_order_time(self, delivery_time, institution_branch):
        preparing_time = timedelta(minutes=institution_branch.preparing_time or 0)
        delivery_duration = timedelta(minutes=institution_branch.max_delivery_time)

        total_time = delivery_time - (preparing_time + delivery_duration)

        return total_time >= timezone.now()

    def _calculate_products_sum(self) -> int:
        item_groups = self.groups
        products_sum = 0

        for group in item_groups:
            for item in group["items"]:
                options_sum = sum([option.adding_price for option in item["options"]])
                product_price = item["product"].price + options_sum
                products_sum += product_price * item["count"]
        products_sum +=  self.instance.package_amount * (self.instance.package_quantity if self.instance.package_quantity > 0 else 1)
        return products_sum

    def _calculate_total_sum_without_discounts(self) -> int:
        result = self.instance.products_sum + self.instance.delivering_sum

        return result

    def _calculate_discount_sum(self) -> int:
        if not self.promo_code_service:
            return 0
        if (
                self.instance.total_sum < self.promo_code_service.get_min_order_sum()
                or self.instance.total_sum < self.promo_code_service.get_sum()
        ):
            raise ValidationError("Total sum is smaller than promo code min sum")
        return self.promo_code_service.get_sum()

    def _calculate_total_sum(self):
        return self.instance.total_sum - self.instance.discount_sum
 
    def _operator_add_with_order(self):
        operator = (
            User.objects.filter(type="operator")
            .annotate(
                order_count=Coalesce(
                    Subquery(
                        Order.objects.filter(
                            Q(operator_id=OuterRef("pk")) & ~Q(status__in=["closed", "rejected"])
                        )
                        .values("operator_id")
                        .annotate(count=Count("id"))
                        .values("count"),
                        output_field=IntegerField(),
                    ),
                    Value(0),
                )
            )
            .order_by("order_count")
            .first()
        )

        if operator:
            self.instance.operator = operator
            self.instance.save(update_fields=["operator"])
        else:
            raise ValidationError("Нет доступных операторов для назначения на заказ")

    def is_institution_available(self, order, institution):
        closest_branch = find_suitable_branch(institution, order.address)

        return closest_branch or False