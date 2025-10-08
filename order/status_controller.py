import time
import logging
from datetime import timedelta


from django.conf import settings
from django.utils import timezone
from django.db import transaction


from ofd.services import OFDReceiptService

from courier.models import Courier, Transaction

from order.helpers import send_message
from order.models import Order
from order.promo_codes.models import PromoCodeUsage
from order.services import payme
from order.serializers import OrderAssignmentValidator
from order.utils import notify_courier, notify_institution, notify_operator
from order.push_notifications.services import notify_ready_order, send_notification, send_notification_to_couriers, send_notification_order_cancel_institution

from payment.models import Payment
from payme.utils import cancel_payment

logger = logging.getLogger(__name__)

def assign_order_to_courier(order_id, courier):
    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(id=order_id)
        except Order.DoesNotExist:
            logger.warning(f"Order {order_id} not found for courier {courier.id}")
            return {'status': False, 'message': {'uz': "Buyurtma topilmadi.", 'ru': "Заказ не найден.", 'en': "Order not found."}}

        validator = OrderAssignmentValidator(order, courier)
        error = validator.validate()
        if error:
            logger.error(f"Order {order_id}, courier {courier.id} | {error}")
            
            return error
       
         # Assign order
        order.courier = courier
        order.timeline.courier_assign_at = timezone.now()
        order.timeline.save()
        order.save()

        # Update courier status
        courier.status = Courier.Status.DELIVERING
        courier.save()

        send_message(order, "courier")

        notify_courier(order)
        notify_operator(order)
        notify_institution(order)

        logger.info(f"Order {order.id} successfully assigned to courier {courier.id}")

        notify_ready_order(order)

        return {'status': True, 'message': {}, 'order': order}



def update_order_status(order: Order, status, preparing_time=None):
    from order.tasks import delayed_send_notification

    error = None
    if order.status != "created" and order.courier is None:
        return False, "Курьер не назначен"
    
    with transaction.atomic():
        if order.status == status:
            logger.info(f"Order {order.id} already has status {status}")
            return False

        # 1. Set status
        order.status = status
        group = order.item_groups.first()
        logger.info(f"Order {order.id} status set to {status}")

        # 2. Handle preparation time
        if preparing_time is not None:
            logger.info(f"Setting preparing time for Order {order.id}: {preparing_time}")
            send_message(order, "accepted", int(preparing_time))
            order.preparing_time = preparing_time

        # 3. Handle status-specific logic
        if status == "accepted":
            logger.info(f"Handling 'accepted' for Order {order.id}")
            if order.is_process:
                return False, "Заказ в процессе обработки стороне заведения"
            
            title = f"Ваш заказ №{order.id} принят заведением"
            body = "Ваш заказ принят и скоро будет готов!"
            
            if order.payment_method == "cash":
                if order.uuid is not None:
                    title = f"Ваш заказ №{order.id} был принят, ждём подтверждения заведения"
                    body = "Ожидаем подтверждения заказа от ресторана. Это может занять до 10-15 минут."
            
                send_notification(order.id, title, body)
                
                if not group.institution.delivery_by_own:
                    send_notification_to_couriers(order_id=order.id)
                    notify_ready_order(order)

            elif order.payment_method == "payme":
                if order.is_paid == False:
                    result = payme(order)
                    print(f"Payme result for Order {order.id}: {result}")
                    if result and result['status'] == 'success':

                        if not group.institution.delivery_by_own:
                            send_notification_to_couriers(order_id=order.id)
                            notify_ready_order(order)

                        send_notification(order.id, title, body)
                        delayed_send_notification.delay(order.id, "Оплата прошла!", f"Спасибо! Платёж успешно завершён для заказа №{order.id}.")
                    else:
                        error = result.get('message', 'Unknown error') if result else 'Unknown error'
                        send_notification(order.id, f"Ошибка оплаты для заказа №{order.id}", error)
                        order.status = "created"
                        
                        send_message(order, "payme_error", 0, error)

                        logger.warning(f"Payme error for Order {order.id}: {error}")

        elif status == "incident":
            logger.info(f"Handling 'incident' for Order {order.id}")
            notify_ready_order(order)
            send_message(order, "incident")
            
        
        elif status == "rejected":
            logger.info(f"Handling 'rejected' for Order {order.id}")
            order.timeline.rejected_at = timezone.now()
            notify_ready_order(order)
            send_notification(order.id, f"Ваш заказ №{order.id} был отклонён", "Заведение не смогло принять заказ.")
            send_message(order, "cancel")
            
            promo = PromoCodeUsage.objects.filter(user_id=order.customer, order=order)
            if promo.exists():
                promo.delete()    
            time.sleep(2)
            send_notification_order_cancel_institution(order.id)
            order.is_paid = False
            
            if order.payment_method == 'payme':
                receipt_id = order.receipt_id
                cancel_payment(receipt_id)
                send_notification(order.id, "Платёж отменён", f"Ваш платёж был отменён.")

        elif status == "closed":
            logger.info(f"Handling 'closed' for Order {order.id}")
            order.timeline.delivered_at = timezone.now()
            branch = order.item_groups.first()
            max_time = branch.institution.max_delivery_time
            
            send_notification(order.id, f"Ваш заказ №{order.id} был доставлен", "Ваш заказ был доставлен! Оставьте отзыв пожалуйста.")

            if order.timeline.courier_take_it_at:
                delta = order.timeline.delivered_at - order.timeline.courier_take_it_at
                minutes = int(delta.total_seconds() / 60)
                order.timeline.courier_lates = abs(max_time - minutes) if max_time < minutes else 0
            
            if not order.is_paid:
                payment = Payment.objects.create(
                    order=order,
                    payment_type="INCOME",
                    payment_method=order.payment_method,
                    amount=order.total_sum,
                    receipt_required=settings.GNK_INTEGRATION_AVAILABLE,
                )
                if settings.GNK_INTEGRATION_AVAILABLE:
                    try:
                        OFDReceiptService(payment).create_sale_receipt()
                    except Exception as e:
                        logger.error(f"OFDReceiptService failed for Order {order.id}: {e}")
                        pass

            group = order.item_groups.first()
            institution = group.institution
            institution.balance -= group.commission  # %
            group.save()
            logger.info(f"Institution Balance updated {institution.balance} for Order {order.id}")

            courier = Courier.objects.filter(order=order).first()
            if order.payment_method == "payme":
                institution.balance += group.products_sum
                Transaction.create_with_balance(courier=courier, order=order, amount=order.delivering_sum, name='delivering', type='in')
                logger.info(f"Courier balance updated {courier.balance} for Order {order.id} delivering in")

                
            if order.payment_method == 'cash':
                if order.uuid is not None or branch.institution.is_holding:
                    Transaction.create_with_balance(courier=courier, order=order, amount=order.products_sum, name='order_amount', type='out')
                    logger.info(f"Courier balance updated {courier.balance} for Order {order.id} order_amount out")
                    
                if order.discount_sum > 0:
                    Transaction.create_with_balance(courier=courier, order=order, amount=order.discount_sum, name='promo_code', type='in')

            if courier.order_set.filter(status__in=["shipped", "accepted"]).count() == 0:
                courier.status = Courier.Status.FREE
            institution.save()

        elif status == "shipped":
            logger.info(f"Handling 'shipped' for Order {order.id}")
            order.timeline.shipped_at = timezone.now()
            order.timeline.preparing_completed_at = timezone.now()
            lates = order.timeline.preparing_completed_at - order.timeline.preparing_start_at
            order.timeline.preparing_lates = lates.total_seconds() / 60 if order.preparing_time else 0
            
        elif status == "ready":
            logger.info(f"Handling 'ready' for Order {order.id}")
            order.timeline.preparing_completed_at = timezone.now()

        # 5. Save everything
        order.save()
        order.timeline.save()
        
        logger.info(f"Order {order.id} and timeline saved")

        # 6. Notify related parties
        if order.status != "created":
            logger.info(f"Notifications sent for Order {order.id}")
            notify_courier(order)
            notify_institution(order)
            notify_operator(order)
        if error is not None:
            logger.error(f"Error occurred while updating order {order.id}: {error}")
            return False, error
        return True, None



# def update_order_status(order: Order, status, preparing_time=None):
#     with transaction.atomic():
#         if order.status == status:
#             return False

#         order.status = status
#         if preparing_time is not None:
#             send_message(order, "accepted", int(preparing_time))
#             order.preparing_time = preparing_time

#         if order.status == "rejected" or order.status == "closed":
#             order.completed_at = timezone.now()
        
#         if order.status == "closed":
#             order.timeline.delivered_at = timezone.now()
#             branch = order.item_groups.first()
#             max_time = branch.institution.max_delivery_time
            
#             if order.timeline.courier_take_it_at:
#                 delta = order.timeline.delivered_at - order.timeline.courier_take_it_at
#                 minutes = int(delta.total_seconds() / 60)
#                 order.timeline.courier_lates = abs(max_time - minutes) if max_time < minutes else 0
        
#         if order.status == "accepted" and order.payment_method == "cash":
#             title = f"Ваш заказ №{order.id} принят заведением"
#             body = "Ваш заказ принят заведением и скоро будет готов!"
            
#             if order.uuid is not None:
#                 title = f"Ваш заказ №{order.id} был принят, ждём подтверждения заведения"
#                 body = "Ожидаем подтверждения заказа от ресторана. Нужно немного подождать - это может занимать да 10-15 минут."

#             send_notification(order.id, title, body)

#         if order.status == "accepted" and order.payment_method == "payme":
#             title = f"Ваш заказ №{order.id} принят заведением"
#             body = "Ваш заказ принят заведением и скоро будет готов!"
#             is_paid = payme(order)
#             if is_paid['status'] == 'success':
#                 send_notification(order.id, title, body)
#                 time.sleep(5)
#                 send_notification(order.id, "Оплата прошла!", f"Спасибо! Платёж успешно завершён.")
#             else:
#                 send_notification(order.id, "Ошибка оплаты", f"Проведение платежа не удалось.\n{is_paid['message']}")
#                 order.status = 'rejected'
#                 time.sleep(5)

#         if order.status == "shipped":
#             order.timeline.courier_take_it_at = timezone.now()
#             send_notification(order.id, f"Ваш заказ №{order.id} в пути", "Ваш заказ в пути, ожидайте курьера")

#         if order.status == "rejected":
#             PromoCodeUsage.objects.filter(user_id=order.customer, order=order).delete()
#             send_notification(order.id, f"Ваш заказ №{order.id} был отменен", "Ваш заказ был отменен!")
#             channel_layer = get_channel_layer()
#             async_to_sync(channel_layer.group_send)(
#                 "ready_orders", {"type": "send_order_status", **AvailableOrdersSerializer(order).data}
#             )
#             send_message(order, "cancel")
#             time.sleep(2)
#             send_notification_order_cancel_institution(order.id)

#         if order.status == "closed":
#             order.timeline.delivered_at = timezone.now()
#             send_notification(order.id, f"Ваш заказ №{order.id} был доставлен", "Ваш заказ был доставлен! Оставьте отзыв пожалуйста.")
            
#         if order.status == "closed":
#             if order.payment_method in ["cash", "terminal"]:
#                 order.is_paid = True
#                 payment = Payment.objects.create(
#                     order=order,
#                     payment_type="INCOME",
#                     payment_method=order.payment_method,
#                     amount=order.total_sum,
#                     receipt_required=settings.GNK_INTEGRATION_AVAILABLE,
#                 )
#                 if settings.GNK_INTEGRATION_AVAILABLE:
#                     try:
#                         OFDReceiptService(payment).create_sale_receipt()
#                     except Exception:
#                         pass
        
#         if order.status == "ready":
#             send_order_courier_ready_notification(order.id)
#             order.timeline.preparing_completed_at = timezone.now()
#             if order.timeline.preparing_start_at:
#                 delta = order.timeline.preparing_completed_at - order.timeline.preparing_start_at
#                 minutes = int(delta.total_seconds() / 60)
                
#                 order.timeline.preparing_lates = abs(order.preparing_time - minutes) if order.preparing_time < minutes else 0
            
#         if order.payment_method == "payme" and status == "rejected":
#             receipt_id = order.receipt_id
#             cancel_payment(receipt_id)
#             order.is_paid = False
#             time.sleep(5)
#             send_notification(order.id, "Платёж отменён", f"Ваш платёж был отменён.")

#         channel_layer = get_channel_layer()
#         group = order.item_groups.first()
        
#         if status == "closed":
#             institution = group.institution
#             institution.balance -= group.commission  # %
#             group.save()

#             courier = Courier.objects.filter(order=order).first()
#             if order.payment_method == "payme":
#                 institution.balance += group.products_sum
                
#                 Transaction.create_with_balance(courier=courier, order=order, amount=order.delivering_sum, type='in')
                
#             if order.payment_method == 'cash':
#                 if order.uuid is not None or branch.institution.is_holding:
#                     Transaction.create_with_balance(courier=courier, order=order, amount=order.products_sum, type='out')
                    
#                 if order.discount_sum > 0:
#                     Transaction.create_with_balance(courier=courier, order=order, amount=order.discount_sum, type='in')

#             if courier.order_set.filter(status__in=["shipped", "accepted"]).count() == 0:
#                 courier.status = Courier.Status.FREE
#             institution.save()
                

#         if group.order.status == "accepted" and (not group.institution.delivery_by_own):
#             if not group.order.self_pickup:
#                 send_notification_to_couriers(order_id=order.id)
#                 async_to_sync(channel_layer.group_send)(
#                     "ready_orders",
#                     {
#                         "type": "send_order_status",
#                         **AvailableOrdersSerializer(instance=group.order).data,
#                         "status": "ready",
#                     },
#                 )
                
#         order.save()
#         order.timeline.save()
        
#         if order.status != "created":
#             notify_courier(order)
#             notify_institution(order)
#             notify_operator(order)
        
#         return True


def cancel_order(order, ignore_constraints=False):
    if not ignore_constraints:
        is_dated = order.created_at + timedelta(minutes=1) < timezone.now()
        has_courier = Courier.objects.filter(order=order).exists()

        if is_dated or has_courier:
            return False, "order is dated or has a courier"

    if not update_order_status(order, "rejected"):
        return False, "unknown error"
   
    return True, "success"

