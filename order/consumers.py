import json

from aiogram import Bot
from aiogram import types
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional
from asgiref.sync import async_to_sync, sync_to_async
from channels.consumer import AsyncConsumer
from channels.generic.websocket import WebsocketConsumer

from order.models import Order, TelegramMessage
from tuktuk.settings import BOT_TOKEN


class OrderCallback(CallbackData, prefix="order"):
    action: str
    order_id: str
    preparing_time: Optional[str] = None

class InstitutionConsumer(WebsocketConsumer):
    def connect(self):
        self.institution_id = self.scope["url_route"]["kwargs"]["institution_id"]
        self.institution_group_name = f"institution_{self.institution_id}"
        async_to_sync(self.channel_layer.group_add)(self.institution_group_name, self.channel_name)

        self.accept()

    def order_data(self, event):
        text_data_to_send = json.dumps(event)
        self.send(text_data=text_data_to_send)

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(self.institution_group_name, self.channel_name)

class OrderConsumer(WebsocketConsumer):
    def connect(self):
        self.client_id = self.scope["url_route"]["kwargs"].get("client_id", None)
        self.group_name = f"client_{self.client_id}"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)

        self.accept()

    def order(self, event):
        text_data_to_send = json.dumps(event)
        self.send(text_data=text_data_to_send)

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)


class OperatorConsumer(WebsocketConsumer):
    def connect(self):
        async_to_sync(self.channel_layer.group_add)("operator", self.channel_name)

        self.accept()

    def order_data(self, event):
        text_data_to_send = json.dumps(event)
        self.send(text_data=text_data_to_send)

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)("operator", self.channel_name)

class CourierConsumer(WebsocketConsumer):
    def connect(self):
        self.courier_group_name = "courier"
        async_to_sync(self.channel_layer.group_add)(self.courier_group_name, self.channel_name)

        self.accept()

    def order_data(self, event):
        text_data_to_send = json.dumps(event)
        self.send(text_data=text_data_to_send)

    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(self.courier_group_name, self.channel_name)

@sync_to_async
def update_message(order_id, text=None, mid=0, mid2=0):
    msg, created = TelegramMessage.objects.get_or_create(order=order_id)
    if created:
        msg = created
    if text is not None:
        msg.text = text
    if mid>0:
        msg.message_id = mid
    if mid2>0:
        msg.message_id2 = mid2
    msg.save()

@sync_to_async
def get_message(order_id):
    msg = TelegramMessage.objects.get(order=order_id)
    if msg:
        return msg
    
class TelegramBotConsumer(AsyncConsumer):
    def __init__(self):
        self.bot = Bot(BOT_TOKEN)
        super(TelegramBotConsumer, self).__init__()

    async def send_cancel_message(self, message=None):
        telegram_id = message["telegram_id"]
        order_id = message["order_id"]
        text = f"Заказ №{order_id} был отменен!"

        await self.bot.send_message(telegram_id, text)

    async def send_message(self, message=None):
        try:
            telegram_id_str = message["telegram_id_str"] or ""
            text = message["text"]
            order_id = message["order_id"]
            status = message.get("status", "create")
            
            keyboard = self.get_keyboard(order_id)
            if status == 'courier' or status == "change_courier":
                keyboard = self.ready_keyboard(order_id)

            if status in ['courier_removed','cooking', 'ready', 'shiped', 'cancel']:
                keyboard = None
            
            has_button = await self.has_button(order_id)
            if  has_button == False:
                keyboard = None
            
            for telegram_id in telegram_id_str.split(" "):
                m=await self.bot.send_message(telegram_id, text, parse_mode="HTML", reply_markup=keyboard)
            m1=await self.bot.send_message("283631065", text, parse_mode="HTML", reply_markup=keyboard)
            
            if status == "new":
                txt = text.replace("<b>Чтобы принять заказ, выберите время приготовления в минутах</b>", "")
                await update_message(order_id=order_id, text=txt, mid=m.message_id, mid2=m1.message_id)

        except Exception as e:
            print("SD", e)
            
    async def edit_message(self, message=None):
        try:
            telegram_id_str = message["telegram_id_str"] or ""
            text = message["text"]
            last_mid = message.get("last_mid", None)
            status = message.get("status", "create")

            # print(text, status)
            
            for telegram_id in telegram_id_str.split(" "):
                if last_mid and last_mid[0] is not None:
                    await self.bot.edit_message_text(chat_id=telegram_id, message_id=last_mid[0], text=text, parse_mode="HTML", reply_markup=None)
                    await self.bot.edit_message_text(chat_id="283631065", message_id=last_mid[1], text=text, parse_mode="HTML", reply_markup=None)

        except Exception as e:
            print("UPDATE", e)
            
    def ready_keyboard(self, order_id):
        keyboard = InlineKeyboardBuilder()
        keyboard.add(
            types.InlineKeyboardButton(
                text="Готов",
                callback_data=OrderCallback(order_id=str(order_id), action="ready").pack(),
            )
        )
        return keyboard.as_markup()
        
    async def has_button(self, order_id):
        @sync_to_async
        def get_order():
            order = (
                Order.objects
                .select_related()
                .prefetch_related('item_groups__institution_branch')
                .get(pk=order_id)
            )
            group = order.item_groups.first()
            return group.institution_branch.is_telegram_orders_enabled
        return await get_order()

    def get_keyboard(self, order_id):
        
        preparing_time_values = (15, 20, 30, 40, 50, 60)
        builder = InlineKeyboardBuilder()

        for value in preparing_time_values:
            builder.button(
                text=f"🕐 {value} мин",
                callback_data=OrderCallback(
                    action="accept", order_id=str(order_id), preparing_time=str(value)
                ).pack(),
            )
        builder.button(
            text="❌ Отклонить",
            callback_data=OrderCallback(action="reject", order_id=str(order_id)).pack(),
        )
        builder.adjust(3, 3, 1,1)  # Har qator 3 tadan button

        keyboard = builder.as_markup()
        return keyboard
    
