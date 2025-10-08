import time
from typing import Iterable

from django.db import transaction

from courier.models import Courier
from order.helpers import send_message
from order.models import Order, OrderItemGroup, OrderItem
# from order.status_controller import send_message
from order.tasks import delayed_notification_task
from order.utils import notify_courier, notify_institution, notify_operator
from product.models import Product, ProductToBranch
from django.utils import timezone


def change_order_courier(order: Order, new_courier: Courier):
    current_courier = order.courier

    if order.status in ["closed", "rejected"]:
        return False, "Order is already completed or cancelled"

    if current_courier:
        if current_courier.order_set.filter(status__in=["shipped", "accepted"]).count() == 0:
            current_courier.status = Courier.Status.FREE
            current_courier.save()
            # TODO: handle courier balance

    order.courier = new_courier
    order.timeline.courier_assign_at = timezone.now()
    order.timeline.preparing_start_at = timezone.now()
    if new_courier:
        order.courier.status = Courier.Status.DELIVERING
        order.courier.save(update_fields=["status"])
    order.save()
    
    notify_courier(order)
    notify_operator(order)
    
    send_message(order, action="change_courier")
    delayed_notification_task.delay(order.id)

    time.sleep(3)
    notify_institution(order)

        
    
    return True, ""


def recalculate_order_products(order: Order):
    item_groups = order.item_groups.all()

    total_sum = 0
    _total_sum = 0
    for group in item_groups:
        products_sum = 0
        _products_sum = 0
        for item in group.items.all():
            items_product_sum = 0
            options_sum = sum([option.adding_price for option in item.options.all()])
            items_product_sum += (item.product.price + options_sum) * item.count
            item.total_sum = items_product_sum
            if item.is_incident:
                _total_sum += items_product_sum
                _products_sum += items_product_sum
            products_sum += items_product_sum
            item.save()
        
        group.total_sum = products_sum + group.delivering_sum - _products_sum
        group.commission = round((products_sum - _products_sum) * (group.institution.tax_percentage_ordinary / 100), -1)
        group.save()
        total_sum += group.total_sum
    
    order.products_sum = products_sum - _products_sum
    discount = order.discount_sum
    order.total_sum = total_sum - discount
    order.save()
    


def add_order_item(order_group: OrderItemGroup, product: Product, count: int, options: Iterable, is_incident: None):
    order = order_group.order
    allowed_statuses = ["pre-order", "created", "pending", "accepted"]

    if order.status not in allowed_statuses:
        return False, f"Cannot add items to this order. Current status: {order.status}"

    with transaction.atomic():

        if is_incident is not None:
            branch = order_group.institution_branch
            
            _product = Product.objects.get(pk=is_incident)
            
            incident_product = ProductToBranch.objects.filter(
                product=_product,
                institution_branches=branch
            ).first()
            
            if incident_product:
                incident_product.is_available = False
                incident_product.save()
                
                print(f"Incident product {incident_product.product.name} marked as unavailable in branch {branch.name} {incident_product.is_available}")

            r = OrderItem.objects.filter(product=_product, order_item_group=order_group).first()
            if r:
                r.is_incident = True
                r.incident_product = product
                r.save()

            # order.status = "incident"
            # order.save()

        # Создаем новый OrderItem
        exists_item = OrderItem.objects.filter(
            order_item_group=order_group,
            product=product,
        ).first()
        print(f"exists_item: {exists_item}", exists_item is not None and len(options) == 0)
        if exists_item:
            exists_options = exists_item.options.all()
            is_new_options = [option for option in options if option not in exists_options]
            

            exists_item.count += count
            exists_item.total_sum += product.price * count
            exists_item.incident_product = _product
            exists_item.is_incident = False           
            item = exists_item

            if is_new_options:
                item = OrderItem.objects.create(
                    order_item_group=order_group,
                    product=product,
                    count=count,
                    total_sum=product.price * count,
                    incident_product=_product if is_incident else None,
                )


        else:    
            item = OrderItem.objects.create(
                order_item_group=order_group,
                product=product,
                count=count,
                total_sum=product.price * count,
                incident_product=_product if is_incident else None,
            )
        # Добавляем стоимость опций к общему итогу
        # item.total_sum += sum([option.adding_price * item.count for option in options])
        item.save()
    
        # Создаем связи между OrderItem и OptionItem
        # _options_through = [
        #     OrderItem.options.through(orderitem=item, optionitem=_option) for _option in options
        # ]
        existing_relations = set(
            OrderItem.options.through.objects
            .filter(orderitem=item, optionitem__in=options)
            .values_list("optionitem_id", flat=True)
        )

        # Faqat mavjud bo‘lmaganlarini bulk_create qilamiz
        _options_through = [
            OrderItem.options.through(orderitem=item, optionitem=_option)
            for _option in options if _option.id not in existing_relations
        ]

        OrderItem.options.through.objects.bulk_create(_options_through)
        
            # return False, str(e)
    # Пересчитываем суммы в заказе
    recalculate_order_products(order)
    return True, item
