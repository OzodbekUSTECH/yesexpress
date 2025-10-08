from aiogram import Bot
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from tuktuk.settings import BOT_TOKEN

channel_layer = get_channel_layer()

ORDER_MESSAGE_TEMPLATE = """
<b>🆕 Новый заказ №{order_id}</b>

<b>Заведение - {institution_name}</b>
<b>Метод оплаты:</b> <i>{payment_method}</i>

<b>🧺 В корзине:</b>
<i>{cart_items}</i>
{package}
Сумма продуктов: <b>{products_sum:,} сум</b>
К оплате: <b>{total_sum:,} сум</b>
{note}
{has_button}
"""

ORDER_ITEM_TEMPLATE = """- {name}{options} x {amount} = {total_sum} сум"""

def get_accept_text(has_button):
    if has_button:
        return "<b>Чтобы принять заказ, выберите время приготовления в минутах</b>"
    return ""

def get_package(order):
    package_quantity = order.package_quantity
    package_amount = order.package_amount
    if package_quantity > 0:
        return f"<i>- Пакет х {package_quantity} = {package_quantity * package_amount}</i>\n"
    return ""

def get_comment(note):
    if note:
        return f"\n<b>Комментарий к заказу:</b>\n<i>{note}</i>"
    return ""

def get_payment_method_display(payment_method):
    if payment_method == "payme":
        return "💳 Payme"
    if payment_method == "cash":
        return "💵 Наличные"
    return "Неизвестно"


class BaseOrderNotifier:
    def __init__(self, order=None):
        self.order = order

    def notify(self, groups=None):
        if not groups:
            groups = self.order.item_groups.all()

        for group in groups:
            self._notify_group(group)

    def _notify_group(self, group):
        raise NotImplementedError


class WebsocketOrderNotifier(BaseOrderNotifier):
    def notify(self, groups=None):
        channel_layer = get_channel_layer()
        if not groups:
            groups = self.order.item_groups.all()
        
        for group in groups:
            async_to_sync(channel_layer.group_send)(
                f"institution_{group.institution_id}",
                # {
                #     "type": "order_data",
                #     "status": self.order.status,
                #     "payment_type": self.order.payment_method,
                #     "order_id": f"{self.order.id}",
                #     "group_id": f"{group.id}",
                #     "products_sum": f"{group.products_sum}",
                #     "created_at": "сейчас",
                #     # "phone_number": f"{self.order.customer.phone_number}",
                #     # "delivering_sum": f"{group.delivering_sum}",
                #     # "discount_sum": f"{self.order.discount_sum}",
                # },
                {
                    "type": "order_data",
                    "status": self.order.status,
                    "payment_type": self.order.payment_method,
                    "order_id": self.order.id,
                    "group_id": group.id,
                    "courier": self.order.courier.id if self.order.courier else None,
                    "products_sum": group.products_sum,
                    "total_sum": group.total_sum + (self.order.package_quantity * self.order.package_amount),
                    "preparing_time": self.order.preparing_time,
                    "institution_name": group.institution.name,
                    "branch_name": group.institution_branch.name,
                    "created_at": self.order.created_at.strftime("%Y-%m-%d")

                }
            )

    def _notify_group(self, group):
        async_to_sync(channel_layer.group_send)(
            f"institution_{group.institution_id}",
            {
                "type": "order_data",
                "status": self.order.status,
                "payment_type": self.order.payment_method,
                "order_id": f"{self.order.id}",
                "group_id": f"{group.id}",
                "products_sum": f"{group.products_sum}",
                "created_at": "сейчас",
                # "phone_number": f"{self.order.customer.phone_number}",
                # "delivering_sum": f"{group.delivering_sum}",
                # "discount_sum": f"{self.order.discount_sum}",
            },
        )


class TelegramOrderNotifier(BaseOrderNotifier):
    def __init__(self, order=None):
        super().__init__(order)
        self.bot = Bot(BOT_TOKEN)

    def _notify_group(self, group):
        telegram_id_str = group.institution_branch.telegram_id_str
        async_to_sync(channel_layer.send)(
            "telegram-notify",
            {
                "type": "send_message",
                "telegram_id_str": telegram_id_str,
                "text": self._get_item_group_text(group),
                "order_id": group.order.id,
                "latitude": float(group.order.address.latitude),
                "longitude": float(group.order.address.longitude),
                "status": "new",
                "last_id": [self.order.message.message_id, self.order.message.message_id2]
            },
        )

    def _get_item_group_text(self, group):

        msg = ORDER_MESSAGE_TEMPLATE.format(
            institution_name=group.institution_branch.name,
            has_button=get_accept_text(group.institution_branch.is_telegram_orders_enabled),
            phone_number=f"+{self.order.customer.phone_number}",
            payment_method=get_payment_method_display(self.order.payment_method),
            cart_items="\n".join(self._get_order_item_text(t) for t in group.items.all()),
            products_sum=group.products_sum,
            delivery_sum=group.delivering_sum,
            total_sum=self.order.products_sum,
            discount_sum=self.order.discount_sum,
            order_id=self.order.id,
            note=get_comment(self.order.note),
            package = get_package(self.order)
        )
        return msg
    
    def _get_order_item_text(self, order_item):
        options = list(order_item.options.all())
        options_text = ""
        if options:
            options_text = " - ".join([f"{option.title_ru}" for option in options])
            options_text = f"({options_text})"

        product_name = order_item.product.name_ru
        if order_item.is_incident:
            product_name = f"{order_item.incident_product.name_ru} (Замена)"
        else:
            if order_item.incident_product:
                product_name = f"{order_item.incident_product.name_ru} (Новый продукт)"
        
        return ORDER_ITEM_TEMPLATE.format(
            name=product_name,
            options=options_text,
            amount=order_item.count,
            total_sum=f"{order_item.total_sum:,}",
        )
