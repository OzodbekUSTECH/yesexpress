import logging
from django.utils import timezone
from datetime import timedelta
import pytz

from drf_yasg.utils import swagger_serializer_method
from fcm_django.api.rest_framework import DeviceSerializerMixin
from fcm_django.models import FCMDevice
from order.feedback.models import DeliveryFeedback, InstitutionFeedback
from order.feedback.serializers import DeliveryFeedbackSerializer, InstitutionFeedbackSerializer
from rest_framework import serializers

from address.serializers import InstitutionAddressSerializer, AddressSerializer
from common.serializer.fields import PrimaryKeyRelatedFieldByUser
from payme.models import PaymeCard
from payment.serializers import PaymentSerializer
from product.serializers import OptionItemSerializer, ThumbnailSerializer
from .models import Order, OrderItem, OrderItemGroup, OrderStatusTimeline
from product.models import OptionItem, Product
from courier.models import Courier
from .promo_codes.models import PromoCode, PromoCodeUsage
from .promo_codes.serializers import PromoCodeInfoSerializer, PromoCodeNotUsedByUserValidator


class OrderFCMDeviceSerializer(DeviceSerializerMixin):
    class Meta(DeviceSerializerMixin.Meta):
        model = FCMDevice


class CourierSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.first_name")
    phone_number = serializers.CharField(source="user.phone_number")
    
    class Meta:
        model = Courier
        fields = ["id", "name", "phone_number", "transport", "car_info", "registration_number"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id", "name_ru", "name_uz", "name_en", "image")


class OrderItemSerializer(serializers.ModelSerializer):
    product_name_ru = serializers.ReadOnlyField(source="product.name_ru")
    product_name_uz = serializers.ReadOnlyField(source="product.name_uz")
    product_name_en = serializers.ReadOnlyField(source="product.name_en")
    options = serializers.PrimaryKeyRelatedField(allow_empty=True, queryset=OptionItem.objects.all(), many=True)
    total_sum = serializers.ReadOnlyField()
    amount = serializers.SerializerMethodField()
    product_obj = ProductSerializer(source="product", many=False, read_only=True)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["options"] = OptionItemSerializer(instance.options.all(), many=True).data
        return rep
        
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_obj",
            "count",
            "options",
            "amount",
            "total_sum",
            "product_name_ru",
            "product_name_uz",
            "product_name_en",
            "is_incident",
        ]

    def get_amount(self, obj):
        return int(obj.total_sum / obj.count)


class OrderItemGroupSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    # created_at = serializers.ReadOnlyField()
    # updated_at = serializers.ReadOnlyField()
    products_sum = serializers.ReadOnlyField()
    delivering_sum = serializers.ReadOnlyField()
    total_sum = serializers.ReadOnlyField()
    institution_name = serializers.ReadOnlyField(source="institution.name")
    institution_logo = ThumbnailSerializer(source="institution.logo", alias="small")

    institution_address = InstitutionAddressSerializer(
        source="institution_branch.address", read_only=True
    )
    institution_branch_name = serializers.ReadOnlyField(source="institution_branch.name")

    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

            
    def get_created_at(self, obj):
        return timezone.localtime(obj.created_at, pytz.timezone("Asia/Tashkent")).isoformat()

    def get_updated_at(self, obj):
        return timezone.localtime(obj.updated_at, pytz.timezone("Asia/Tashkent")).isoformat()
    class Meta:
        model = OrderItemGroup
        fields = [
            "id",
            "institution",
            "institution_name",
            "institution_logo",
            "institution_address",
            "institution_branch",
            "institution_branch_name",
            "items",
            "products_sum",
            "delivering_sum",
            "total_sum",
            "created_at",
            "updated_at",
        ]

class OrderTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusTimeline
        fields = ["preparing_start_at", "preparing_completed_at", "preparing_lates", "courier_assign_at", "courier_arrived_at", "courier_take_it_at", "courier_lates", "delivered_at"]

class OrderSerializer(serializers.ModelSerializer):
    item_groups = OrderItemGroupSerializer(many=True)
    customer = serializers.IntegerField(source="customer.id", read_only=True)
    status = serializers.ReadOnlyField()
    # created_at = serializers.ReadOnlyField()
    # updated_at = serializers.ReadOnlyField()
    is_paid = serializers.ReadOnlyField()
    products_sum = serializers.ReadOnlyField()
    delivering_sum = serializers.ReadOnlyField()
    total_sum = serializers.ReadOnlyField()
    address_coordinates = AddressSerializer(read_only=True, source="address")
    operator = serializers.CharField(source="operator.id", read_only=True)
    timeline = OrderTimelineSerializer(read_only=True)
    delivery_time = serializers.DateTimeField(required=False, allow_null=True)
    # fcm_device = OrderFCMDeviceSerializer(allow_null=True)
    courier = CourierSerializer(read_only=True, allow_null=True)
    
    promo_code = serializers.SlugRelatedField(
        queryset=PromoCode.objects.filter_usable(),
        slug_field="code",
        required=False,
        allow_null=True,
        write_only=True,
        validators=[PromoCodeNotUsedByUserValidator()],
    )
    payment = serializers.SerializerMethodField(read_only=True, allow_null=True)
    card = PrimaryKeyRelatedFieldByUser(
        queryset=PaymeCard.objects.all(), allow_null=True, required=False
    )
    # prices = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()
    institution = serializers.SerializerMethodField()
    discount_sum = serializers.SerializerMethodField(read_only=True, allow_null=True)
    institution_feedback = serializers.SerializerMethodField(read_only=True, allow_null=True)
    delivery_feedback = serializers.SerializerMethodField(read_only=True, allow_null=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    updated_at = serializers.SerializerMethodField(read_only=True)

            
    def get_created_at(self, obj):
        return timezone.localtime(obj.created_at, pytz.timezone("Asia/Tashkent")).isoformat()

    def get_updated_at(self, obj):
        return timezone.localtime(obj.updated_at, pytz.timezone("Asia/Tashkent")).isoformat()
    
    class Meta:
        model = Order
        fields = [
            "id",
            "note",
            "item_groups",
            # "prices",
            "products",
            "institution",
            "payment_method",
            "customer",
            "status",
            "is_paid",
            "address",
            "created_at",
            "updated_at",
            "is_paid",
            "discount_sum",
            "products_sum",
            "delivering_sum",
            "total_sum",
            "preparing_time",
            "courier",
            "address_coordinates",
            "promo_code",
            "operator",
            "delivery_time",
            "timeline",
            "payment",
            "card",
            "institution_feedback",
            "delivery_feedback",
            "package_amount",
            "package_quantity",
        ]
        
    def get_institution(self, obj):
        item_groups = obj.item_groups.first()
        branch = item_groups.institution_branch

        institution_data = {
            "name": item_groups.institution.name,
            "logo": item_groups.institution.logo.url if item_groups.institution.logo else "",
            "min_delivery_time": item_groups.institution.min_delivery_time,
            "max_delivery_time": item_groups.institution.max_delivery_time,
        }
        if branch:
            address = branch.address
            institution_data["branch"] = {
                "name": branch.name,
                "is_open": branch.is_open,
                "phone_number": branch.phone_number,
                "start_time": branch.start_time,
                "end_time": branch.end_time,
                "address": {
                    "street": address.street,
                    "reference_point": address.reference_point,
                    "latitude": address.latitude,
                    "longitude": address.longitude,
                }
            }
        
        return institution_data
         
    def get_products(self, obj):
        products = []
        for group in obj.item_groups.all():
            for item in group.items.all():
                product = {
                    "id": item.id,
                    "name_ru": item.product.name_ru,
                    "name_uz": item.product.name_uz,
                    "name_en": item.product.name_en,
                    "image": item.product.image.url if item.product.image else None,
                    "count": item.count,
                    "amount": item.product.price,
                    "total": item.count * item.product.price,
                    "options":  OptionItemSerializer(item.options.all(), many=True).data,
                }
                products.append(product)
        return products
        
    def get_discount_sum(self, obj):
        try:
            promo = PromoCodeUsage.objects.select_related("promo_code").get(order=obj, user=obj.customer)
            if promo:
                promocode = promo.promo_code.sum
        except PromoCodeUsage.DoesNotExist:
            promocode = 0
        return promocode
        
    # def get_prices(self, obj):
    #     promocode = 0
    #     try:
    #         promo = PromoCodeUsage.objects.select_related("promo_code").get(order=obj, user=obj.customer)
    #         if promo:
    #             promocode = promo.promo_code.sum
    #     except PromoCodeUsage.DoesNotExist:
    #         pass
    #     price_info = {
    #         "discount_amount":  promocode,
    #         "delivery_amount":  obj.delivering_sum,
    #         "restaurant_amount": obj.products_sum,
    #         "total_amount": obj.delivering_sum + obj.products_sum - promocode
    #     }
    #     return price_info
    
    def get_institution_feedback(self, obj):
        feedback = InstitutionFeedback.objects.filter(order=obj).first()
        if feedback:
            return InstitutionFeedbackSerializer(feedback).data
        return None

    def get_delivery_feedback(self, obj):
        feedback = DeliveryFeedback.objects.filter(order=obj).first()
        if feedback:
            return DeliveryFeedbackSerializer(feedback).data
        return None

    @swagger_serializer_method(PaymentSerializer())
    def get_payment(self, obj: Order):
        payment = obj.payment_set.filter(is_active=True, is_deleted=False).first()
        if payment:
            return PaymentSerializer(payment).data
        return None

    def validate(self, data):
        status = data.get("status")
        delivery_time = data.get("delivery_time")
        if status == "pre_order":
            if not delivery_time:
                raise serializers.ValidationError(
                    "Для предзаказа необходимо указать время доставки"
                )

            item_groups = data.get("item_groups", [])
            if not item_groups:
                raise serializers.ValidationError("Не указаны группы товаров")

            institution_branch = item_groups[0].get("institution_branch")
            if not institution_branch:
                raise serializers.ValidationError("Не указан филиал заведения.")

            min_delivery_time = timezone.now() + timedelta(
                minutes=institution_branch.min_preorder_minutes
            )
            if delivery_time < min_delivery_time:
                raise serializers.ValidationError(
                    f"Время доставки должно быть не раньше чем через {institution_branch.min_preorder_minutes} минут"
                )

            max_preorder_date = timezone.now() + timedelta(
                days=institution_branch.max_preorder_days
            )
            if delivery_time > max_preorder_date:
                raise serializers.ValidationError(
                    f"Предзаказ возможен только на {institution_branch.max_preorder_days} дней вперед"
                )

            if not self.is_valid_delivery_time(delivery_time, institution_branch):
                raise serializers.ValidationError("Заведение не работает в указанное время.")

            if not self.is_valid_order_time(delivery_time, institution_branch):
                raise serializers.ValidationError(
                    "Общее время выполнения заказа превышает время работы заведения"
                )

        return data

    def is_valid_delivery_time(self, delivery_time, institution_branch):
        delivery_time = delivery_time.time()

        return institution_branch.start_time <= delivery_time <= institution_branch.end_time

    def is_valid_order_time(self, delivery_time, institution_branch):
        preparing_time = timedelta(minutes=institution_branch.preparing_time or 0)
        delivery_duration = timedelta(minutes=institution_branch.max_delivery_time)

        total_time = delivery_time - (preparing_time + delivery_duration)

        return total_time >= timezone.now()

class OrderRestaurantSerializer(OrderSerializer):
    total_sum = serializers.SerializerMethodField()
    prices = serializers.SerializerMethodField()
    package = serializers.SerializerMethodField()
   
    timeline = OrderTimelineSerializer(read_only=True)
    
    class Meta(OrderSerializer.Meta):
        model = OrderSerializer.Meta.model
        
        fields = (
            "id",
            "note",
            "status",
            "item_groups",
            "payment_method",
            "is_paid",
            "prices",
            "products_sum",
            "delivering_sum",
            "total_sum",
            "preparing_time",
            "timeline",
            "courier",
            "operator",
            "is_process",
            "delivery_time",
            "payment",
            "card",
            "package",
            "institution_feedback",
            "delivery_feedback",
            "created_at",
            "updated_at"
        )
    
    def get_package(self, obj):
        if obj.package_amount > 0:
            return {"package_amount": obj.package_amount, "package_quantity": obj.package_quantity}
        return None

    def get_prices(self, obj):
        promocode = 0
        try:
            promo = PromoCodeUsage.objects.select_related("promo_code").get(order=obj, user=obj.customer)
            if promo:
                promocode = promo.promo_code.sum
        except PromoCodeUsage.DoesNotExist:
            pass
        
        price_info = {
            "discount_amount":  promocode,
            "delivery_amount":  obj.delivering_sum,
            "restaurant_amount": obj.products_sum,
            "total_amount": obj.delivering_sum + obj.products_sum - promocode
        }
        return price_info
    
    def get_total_sum(self, obj):
        return obj.products_sum
    

logger = logging.getLogger(__name__)
class OrderAssignmentValidator:
    def __init__(self, order, courier):
        self.order = order
        self.courier = courier

    def validate(self):

        if self.order.self_pickup:
            logger.error(f"Order {self.order.id} is self-pickup, courier {self.courier.id} rejected")
            return self._error([
                "Kechirasiz, bu buyurtmani mijoz o‘zi olib ketishni tanlagan.", 
                "Извините, клиент выбрал самовывоз для этого заказа.",
                "Sorry, the customer has chosen to pick up this order themselves."
            ])

        if self.order.item_groups.filter(institution__delivery_by_own=True).exists():
            logger.error(f"Order {self.order.id} is delivered by institution's own courier")
            return self._error([
                "Ushbu buyurtma muassasaning o'z yetkazib berish xizmati tomonidan yetkazib berilishi kerak.",
                "Данный заказ должен быть доставлен собственной службой доставки учреждения.",
                "This order must be delivered by the institution's own delivery service."
            ])

        if self.order.courier and self.order.courier is not None:
            logger.error(f"Order {self.order.id} is already assigned to courier {self.order.courier.id}")
            return self._error([
                "Kechirasiz, bu buyurtma allaqachon boshqa kuryerga topshirilgan.",
                "Извините, этот заказ уже передан другому курьеру.",
                "Sorry, this order has already been assigned to another courier."
            ])

        if Order.objects.filter(courier=self.courier, status__in=["accepted", "shipped"]).count() >= 3:
            logger.info(f"Courier {self.courier.id} reached active order limit")
            return self._error([
                "Kechirasiz, sizda ruxsat etilgan limit doirasida faol buyurtmalar mavjud. Yangi buyurtma olish uchun avval mavjud buyurtmalarni yakunlang.",
                "Извините, у вас уже есть активные заказы в пределах допустимого лимита. Пожалуйста, завершите текущие заказы, прежде чем принимать новые.",
                "Sorry, you already have active orders within your allowed limit. Please complete your current orders before accepting a new one."
            ])

        institution = self.order.item_groups.first().institution
        if self.order.payment_method == "cash" and (self.order.uuid or institution.is_holding):
            if self.courier.balance < self.order.total_sum:
                logger.error(f"Order {self.order.id} not found for courier {self.courier.id}")
                return self._error([
                    "Kechirasiz, buyurtmani rasmiylashtirish uchun balansingizda yetarli mablag' mavjud emas.",
                    "Извините, на вашем балансе недостаточно средств для оформления заказа.",
                    "Sorry, you don't have enough balance to complete the order."
                ])

        return None

    def _error(self, message):
        return {
            'status': False,
            'message': {
                'uz': message[0],
                'ru': message[1],
                'en': message[2],
            }
        }