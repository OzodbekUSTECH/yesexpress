from celery import shared_task
import time

from order.models import Order
from order.push_notifications.services import send_notification
from order.status_controller import update_order_status
from rkeeper.services import rkeeperAPI
from django.utils import timezone
from django.db.models import Q

@shared_task
def delayed_notification_task(order_id):
    time.sleep(60)
    order = Order.objects.get(pk=order_id)

    group = order.item_groups.first()
    institution = group.institution
    if institution and institution.client_id and institution.client_secret and institution.endpoint_url and order.courier is not None:
        rkeeper = rkeeperAPI(client_id=institution.client_id, client_secret=institution.client_secret, endpoint_url=institution.endpoint_url)
        rkeeper.make_order(order)

@shared_task
def delayed_send_notification(order_id, title, body):
    time.sleep(3)
    send_notification(order_id, title, body)
    
@shared_task
def bulk_check_order_statuses():
    orders = Order.objects.filter(status="accepted", uuid__isnull=False).filter(
        Q(restaurant_status__isnull=True) | Q(restaurant_status__in=['NEW', 'COOKING', 'ACCEPTED_BY_RESTAURANT'])
    )

    for order in orders:
        group = order.item_groups.first()
        institution = group.institution
        rkeeper = rkeeperAPI(client_id=institution.client_id, client_secret=institution.client_secret)
        response = rkeeper.get_order_status(order.uuid)
        if response and isinstance(response, dict):
            status = response.get('status', None)

        if status in ['NEW', 'COOKING', 'ACCEPTED_BY_RESTAURANT', 'READY', 'CANCELLED']:
            if order.restaurant_status != status:
                try:
                    order.restaurant_status = status
                    order.save(update_fields=["restaurant_status"])
                    print(f"updated {order.restaurant_status}")
                except Exception as e:
                    print("Error on change statys", status, e)

                if status == 'ACCEPTED_BY_RESTAURANT':
                    order.timeline.preparing_start_at = timezone.now()
                    order.timeline.save()

                    send_notification(order.id, f"Ваш заказ №{order.id} принят заведением", "Ваш заказ принят заведением и скоро будет готов!")

                if status == 'READY':
                    update_order_status(order, "ready")

                if status == 'CANCELLED':
                    update_order_status(order, "rejected")