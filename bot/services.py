import asyncio
from textwrap import dedent
from typing import Union

from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import html_decoration as hd

from asgiref.sync import sync_to_async

from courier.models import Courier
from order.consumers import OrderCallback, get_message, update_message
from order.models import ORDER_STATUS, Order, OrderItemGroup
from order.status_controller import cancel_order, update_order_status

from django.utils import timezone

def get_status_keyboard(order):
    return types.InlineKeyboardButton(
        text=f"Статус: {order.get_status_display()}",
        callback_data=OrderCallback(order_id=order.id, action="status").pack(),
    )


async def get_order(order_id: int):
    return await Order.objects.aget(pk=order_id)

async def get_timeline(order_id: int):
    from datetime import datetime, timedelta, timezone
    order = await Order.objects.select_related("timeline").aget(pk=order_id)
    preparing_time = order.preparing_time
    preparing_start_at = order.timeline.preparing_start_at
    if preparing_start_at is None:
        return False
    deadline = preparing_start_at + timedelta(minutes=preparing_time)
    now = datetime.now(timezone.utc)
    return now > deadline


async def get_item_group(order_id: int):
    return await sync_to_async(OrderItemGroup.objects.select_related("institution").get)(
        order_id=order_id
    )


async def get_courier(order: Order):
    courier_qs = await sync_to_async(Courier.objects.select_related("user").filter)(
        pk=order.courier_id
    )
    courier = await sync_to_async(courier_qs.first)()
    return courier


async def get_courier_info(courier: Courier):
    info = dedent(
        "\n\n"
        "Информация о курьере:\n"
        f"Имя: {courier.user.first_name}\n"
        f"Номер телефона: +{courier.user.phone_number} -"
    )
    return info


async def update_status(call: types.CallbackQuery, order_id: int, callback_data: dict):
    order = await get_order(order_id)
    message = call.message
    reply_markup = message.reply_markup
    new_status_keyboard = get_status_keyboard(order)
    reply_markup.inline_keyboard[0].pop()
    reply_markup.inline_keyboard[0].append(new_status_keyboard)

    await message.edit_reply_markup(reply_markup=reply_markup)

locks = {}

async def accept_order(
    call: types.CallbackQuery,
    order_id: int,
    callback_data: OrderCallback,
):
    if order_id not in locks:
        locks[order_id] = asyncio.Lock()
    async with locks[order_id]:
        order = await Order.objects.aget(pk=order_id)
        preparing_time = callback_data.preparing_time
        success = await sync_to_async(update_order_status)(order, "accepted", int(preparing_time))
        if success:
            await call.answer()

async def prepare_order(
    call: types.CallbackQuery,
    order_id: int,
    callback_data: OrderCallback,
):
    order = await Order.objects.aget(pk=order_id)
    
    if order.status == ORDER_STATUS.COOKING:
        await call.message.edit_reply_markup(reply_markup=None)
        return await call.answer("Заказ уже в процессе...", show_alert=True)
    
    success = await sync_to_async(update_order_status)(order, "cooking")
    if success:
        await call.message.edit_reply_markup(reply_markup=None)
 
async def reject_order(
    call: types.CallbackQuery,
    order_id: int,
    callback_data: OrderCallback,
):
    if order_id not in locks:
        locks[order_id] = asyncio.Lock()

    async with locks[order_id]:
        order = await Order.objects.aget(pk=order_id)
        print(order.status)
        success = await sync_to_async(update_order_status)(order, "rejected")
        if success:
            await call.answer()

async def ready_order(
    call: types.CallbackQuery,
    order_id: int,
    callback_data: OrderCallback,
):
    if order_id not in locks:
        locks[order_id] = asyncio.Lock()

    async with locks[order_id]:
        order = await get_order(order_id)
        deadline = await get_timeline(order_id)

        if not deadline:
            await call.answer("Заказ еще не готов!", show_alert=True)
            return
        
        if order.status == 'ready':
            await call.answer("Заказ был готов недавно!", show_alert=True)
            await call.message.edit_reply_markup(reply_markup=None)
            return
                 
        success = await sync_to_async(update_order_status)(order, "ready")
        if success:
            keyboard = InlineKeyboardBuilder()
            item_group = await get_item_group(order_id)
            if item_group.institution.delivery_by_own:
                keyboard.add(
                    types.InlineKeyboardButton(
                        text="В пути",
                        callback_data=OrderCallback(order_id=order_id, action="shipping").pack(),
                    ),
                )
            await call.message.edit_reply_markup(reply_markup=keyboard.as_markup())


async def shipping_order(call: types.CallbackQuery, order_id: int, callback_data: dict):
    order = await get_order(order_id)
    if order.status == 'shipped':
        await call.answer("Заказ был доставлен недавно!", show_alert=True)
        await call.message.edit_reply_markup(reply_markup=None)
        return
    success = await sync_to_async(update_order_status)(order, "shipped")

    if success:
        keyboard = InlineKeyboardBuilder()
        item_group = await get_item_group(order_id)
        if item_group.institution.delivery_by_own:
            keyboard.add(
                types.InlineKeyboardButton(
                    text="Завершить",
                    callback_data=OrderCallback(order_id=order_id, action="close").pack(),
                ),
            )
        keyboard.add(get_status_keyboard(order))
        await call.message.edit_reply_markup(reply_markup=keyboard.as_markup())


async def close_order(call: types.CallbackQuery, order_id: int, callback_data: dict):
    order = await get_order(order_id)
    if order.status == 'closed':
        await call.answer("Заказ был закрыт недавно!", show_alert=True)
        await call.message.edit_reply_markup(reply_markup=None)
        return
    success = await sync_to_async(update_order_status)(order, "closed")
    if success:
        keyboard = InlineKeyboardBuilder()
        keyboard.add(get_status_keyboard(order))
        await call.message.edit_reply_markup(reply_markup=keyboard.as_markup())


async def update_courier(call: types.CallbackQuery, order_id: int, callback_data: dict):
    order = await get_order(order_id)
    courier = await get_courier(order)
    if not courier:
        await call.answer(text="У заведения пока нет курьера", show_alert=True)
        return
    message = call.message
    message_text = message.text
    if message_text[-1] != "-":
        courier_info = await get_courier_info(courier)
        result_message = message_text + courier_info
        await message.edit_text(result_message, reply_markup=message.reply_markup)
