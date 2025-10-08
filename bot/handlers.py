from aiogram import types, Dispatcher

from order.consumers import OrderCallback
from . import services

dp = Dispatcher()

@dp.callback_query(OrderCallback.filter())
async def button_pressed(call: types.CallbackQuery, callback_data: OrderCallback):
    try:
        action = callback_data.action
        order_id = callback_data.order_id
        actions = {
            "accept": services.accept_order,
            "reject": services.reject_order,
            "ready": services.ready_order,
            "shipping": services.shipping_order,
            "close": services.close_order,
            "courier": services.update_courier,
            "status": services.update_status,
        }

        await actions[action](call=call, order_id=order_id, callback_data=callback_data)
        await call.answer()
    except Exception as e:
        print("EX", e)

