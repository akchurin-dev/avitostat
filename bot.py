import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from dotenv import load_dotenv

from bot.week_report import get_week_report_text
from telegram_bot.cleaner.cleaner import Cleaner
from telegram_bot.cleaner.cleaner_middleware import CleanerMiddleware

load_dotenv()
# t.me/avitostata_bot

logging.basicConfig(level=logging.INFO)

router = Router()


@router.message()
async def echo(message: Message, cleaner):
    msg = message.text.lower()
    if msg == "/week@avitostata_bot":
        text = await get_week_report_text(message=message)
        while text:
            await message.answer(text=text[:4000], parse_mode=ParseMode.HTML)
            text = text[4000:]
    elif msg in ["/help@avitostata_bot", "/help", "help"]:
        await message.reply("/help - список команд \n"
                            "/week - еженедельный отчёт \n")
    else:
        pass


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
