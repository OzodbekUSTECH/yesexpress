import logging
from aiogram import Bot
from tuktuk.settings import BOT_TOKEN
from .handlers import dp


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    async with Bot(token=BOT_TOKEN) as bot:
        
        print("***** Start polling *****")
        await dp.start_polling(bot)
