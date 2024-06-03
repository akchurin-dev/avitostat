import asyncio
import logging
import os
import sys
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from dotenv import load_dotenv

from bot.week_report import get_week_report_text
from telegram_bot.api.week_report import get_avito_account_all_ids
from telegram_bot.cleaner.cleaner import Cleaner
from telegram_bot.cleaner.cleaner_middleware import CleanerMiddleware

load_dotenv()
# t.me/avitostata_bot

bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)
router = Router()

scheduler = AsyncIOScheduler()  # Автоматическая отправка сообщений


async def scheduler_setup(scheduler: AsyncIOScheduler, bot):
    scheduler.add_job(send_week_report_to_all_accounts, "interval",
                      minutes=15,
                      args=(bot,))

    scheduler.start()


async def send_week_report_to_all_accounts():
    avito_account_ids = get_avito_account_all_ids()
    if avito_account_ids:
        for account_id in avito_account_ids:
            await send_week_report(int(account_id))


async def send_week_report(telegram_chat_id: int):
    text = await get_week_report_text(telegram_chat_id, bot=bot)

    while text:
        await bot.send_message(
            chat_id=telegram_chat_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
        text = text[4000:]


@router.message()
async def echo(message: Message, bot: Bot):
    msg = message.text.lower()
    if msg == "/week@avitostata_bot":
        await send_week_report(message.chat.id)

    if msg == "/week_all@avitostata_bot":
        await send_week_report_to_all_accounts()

    elif msg in ["/help@avitostata_bot", "/help", "help"]:
        await message.reply("/help - список команд \n"
                            "/week - еженедельный отчёт \n"
                            "/week_all - еженедельный отчёт всем \n")
    else:
        pass


async def main() -> None:
    dp.include_router(router)

    cleaner = Cleaner(limit=100)
    dp.update.middleware(CleanerMiddleware(cleaner))

    await scheduler_setup(scheduler, bot)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
