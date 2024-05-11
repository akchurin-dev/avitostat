import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from dotenv import load_dotenv

from telegram_bot.cleaner.cleaner import Cleaner
from telegram_bot.cleaner.cleaner_middleware import CleanerMiddleware

load_dotenv()
# t.me/avitostata_bot

logging.basicConfig(level=logging.INFO)

router = Router()


async def week_report(message: Message):
    await message.answer(
        "wait minet i will send you info"
    )


@router.message()
async def echo(message: Message, cleaner):
    msg = message.text.lower()
    if msg == "week":
        await week_report(message=message)
    else:
        await message.answer(msg)


async def main() -> None:
    bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
    dp = Dispatcher()

    dp.include_router(router)

    cleaner = Cleaner(limit=100)
    dp.update.middleware(CleanerMiddleware(cleaner))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
