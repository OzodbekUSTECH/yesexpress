
from email.mime import message
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from django.utils import timezone
from order.push_notifications.services import send_notification

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

def edit_msg(telegram_id, text, status, last_mid):

    async_to_sync(channel_layer.send)(
        "telegram-notify",
        {
            "type": "edit_message",
            "telegram_id_str": telegram_id,
            "text": text,
            "status": status,
            "last_mid": last_mid,
        },
    )

def send_msg(telegram_id, text, order_id, status, last_mid):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.send)(
        "telegram-notify",
        {
            "type": "send_message",
            "telegram_id_str": telegram_id,
            "text": text,
            "order_id": order_id,
            "status": status,
            "last_mid": last_mid,
        },
    )

def send_message(order, action, preparing_time=0, error=None):
    msg = ""
    message = getattr(order, "message", None)
    if not message:
        last_id = [None, None]
    else:
        last_id = [order.message.message_id, order.message.message_id2]
        msg = order.message.text

    ico = {"car": "🚙", "scooter": "🛵", "foot": "🚶‍♂️"}
    types = {"car": "🚙 машина", "scooter": "🛵 скутер", "foot": "🚶‍♂️ пешком"}
    
    courier = order.courier
    
    group = order.item_groups.first()
    telegram_id = group.institution_branch.telegram_id_str
    text = None
    if action == "payme_error":
        if msg is not None:
            text = msg.rstrip("\n") + f"\n<b>❌ Ошибка оплаты</b>\n{preparing_time}"
            edit_msg(telegram_id, text, "payme_error", last_id)
            logger.info(f"Payme error message edited for order {order.id}")
        return
    
    if action == "accepted" and preparing_time > 0:
        if msg is not None:
            text = msg.rstrip("\n") + f"\n✅ <b>Заказ принят</b>\n⏳ Время приготовления: <b>{preparing_time} мин</b>"
            edit_msg(telegram_id, text, "accepted", last_id)
            logger.info(f"Accepted message edited for order {order.id}")
        return
    
    if action == "incident":
        if msg is not None:
            text = msg.rstrip("\n") + f"\n<b>❗️ Замена продукта в заказе</b>"
            edit_msg(telegram_id, text, "incident", last_id)
            logger.info(f"Incident message edited for order {order.id}")
        return
    
    if courier:
        courier_info = types[courier.transport]
        order.timeline.preparing_start_at = timezone.now()
        order.timeline.save()
    

    if action in ("courier", "change_courier"):

        if courier:
            if not courier.transport:
                logger.warning(f"Courier transport type missing for order {order.id}")
                return
            courier_info = types.get(courier.transport, "неизвестный транспорт")
            transport_icon = ico.get(courier.transport, "")

            send_notification(
                order.id,
                f"На ваш заказ №{order.id} назначен курьер",
                f"К заказу №{order.id} назначен курьер. Ожидайте доставку в ближайшее время.",
            )

            order.timeline.preparing_start_at = timezone.now()
            order.timeline.save()
            courier_detail = (
                f"Информация о курьере:</b>\n"
                f"Имя: {courier.user.first_name}\n"
                f"Номер телефона: +{courier.user.phone_number.replace('+','')}\n"
                f"Транспорт: {courier_info}"
            )

        if action == "courier":
            title = f"<b>{transport_icon} Заказ №{order.id} принят курьером, начинайте готовить.\n\n"
        elif action == "change_courier":
            if not courier:
                logger.warning(f"Courier not found for order {order.id}")
                title = f"<b>Курьер снят с заказа №{order.id}</b>\n\n"
                action = "courier_removed"
            else:
                title = f"<b>{transport_icon} Курьер переназначен для заказ №{order.id}\n\n"
            

        if courier and courier_detail:
            text = title + courier_detail
        else:
            text = title
        
    elif action == "cancel":
        if msg:
            edited_msg = msg.rstrip("\n") + f"\n<b>❌ Заказ отменен</b>."
            edit_msg(telegram_id, edited_msg, action, last_id)
        text = f"<b>❌ Заказ №{order.id} отменен</b>."

    if text:
        send_msg(telegram_id, text, order.id, action, last_id)
        logger.info(f"Message sent to Telegram for order {order.id} with status '{action}'")
    else:
        logger.warning(f"No message text generated for action '{action}' on order {order.id}")

    
