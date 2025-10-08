import time
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .notifiers import WebsocketOrderNotifier, TelegramOrderNotifier


def notify(order, notifier_classes=None):
    if not notifier_classes:
        notifier_classes = [WebsocketOrderNotifier, TelegramOrderNotifier]
    for notifier_class in notifier_classes:
        notifier = notifier_class(order)
        notifier.notify()
        time.sleep(1)

    notify_operator(order)

def notify_operator(order):
    channel_layer = get_channel_layer()
    for group in order.item_groups.all():
        async_to_sync(channel_layer.group_send)(
            "operator",
            {
                "type": "order_data",
                "status": order.status,
                "payment_type": order.payment_method,
                "order_id": order.id,
                "group_id": group.id,
                "preparing_time": order.preparing_time,
                "phone_number": order.customer.phone_number,
                "products_sum": group.products_sum,
                "total_sum": group.total_sum,
                "courier": order.courier.id if order.courier else None,
                "delivering_sum": group.delivering_sum,
                "created_at": order.created_at.strftime("%Y-%m-%d"),
                "institution_name": group.institution.name,
                "branch_name": group.institution_branch.name
            },
        )
        async_to_sync(channel_layer.group_send)(
            f"client_{order.customer.id}",
            {
                "type": "order",
                "status": order.status,
                "order_id": order.id,
            },
        )

def notify_institution(order):
    channel_layer = get_channel_layer()
    for group in order.item_groups.all():
        async_to_sync(channel_layer.group_send)(
            f"institution_{group.institution.id}",
            {
                "type": "order_data",
                "status": order.status,
                "payment_type": order.payment_method,
                "order_id": order.id,
                "group_id": group.id,
                "courier": order.courier.id if order.courier else None,
                "products_sum": group.products_sum,
                "total_sum": group.total_sum,
                "preparing_time": order.preparing_time,
                "institution_name": group.institution.name,
                "branch_name": group.institution_branch.name,
                "created_at": order.created_at.strftime("%Y-%m-%d")

            },
        )

def notify_courier(order):
    channel_layer = get_channel_layer()
    for group in order.item_groups.all():
        async_to_sync(channel_layer.group_send)(
            f"courier",
            {
                "type": "order_data",
                "status": order.status,
                "payment_type": order.payment_method,
                "order_id": f"{order.id}",
                "group_id": f"{group.id}",
                "courier": order.courier.id if order.courier else None,

                "preparing_time": order.preparing_time,
                "phone_number": f"{order.customer.phone_number}",
                "products_sum": f"{group.products_sum}",
                "delivering_sum": f"{group.delivering_sum}",
                "institution_name": f"{group.institution.name}",
            },
        )


