from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from courier.serializers import AvailableOrdersSerializer


# Courier #
def notify_ready_order(order):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "ready_orders",
        {
            "type": "send_order_status",
            **AvailableOrdersSerializer(order).data
        }
    )
# Courier #



def send_notification(order_id, title, body):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.send)(
        "firebase-notify",
        {"type": "send_notification", "order_id": order_id, "title": title, "body": body},
    )


def send_notification_to_couriers(order_id):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.send)("firebase-notify", {"type": "courier_new_order_notification", "order_id": order_id})


def send_notification_to_institution(order_id):
    print(f"🔔 New order notification: Order #{order_id}")
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.send)(
        "firebase-notify",
        {"type": "institution_new_order_notification", "order_id": order_id},
    )


def send_notification_courier_accept_to_institution(order_id):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.send)(
        "firebase-notify",
        {"type": "institution_courier_accept_notification", "order_id": order_id},
    )

def send_notification_order_cancel(order_id):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.send)(
        "firebase-notify",
        {"type": "institution_courier_accept_notification", "order_id": order_id},
    )

def send_notification_order_cancel_institution(order_id):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.send)(
        "firebase-notify",
        {"type": "institution_cancel_notification", "order_id": order_id},
    )

def send_order_courier_ready_notification(order_id):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.send)(
        "firebase-notify",
        {"type": "order_courier_ready_notification", "order_id": order_id},
    )

