import asyncio
import logging
import os
import sys

import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from dotenv import load_dotenv
from tg_bot.api.week_report import get_pdf_report_all_to_users, \
    get_pdf_report_all_to_admin
from tg_bot.cleaner.cleaner import Cleaner
from tg_bot.cleaner.cleaner_middleware import CleanerMiddleware

# Инициализация Sentry
sentry_sdk.init(
    dsn="https://aa9aa3ef5af1cd3d0b5ace8a5dd9e5a2@o4506274465972224.ingest.us.sentry.io/4507378965086208",
    traces_sample_rate=1.0,  # Это процент отслеживаемых транзакций, можно настроить по необходимости
    profiles_sample_rate=1.0,
)

load_dotenv()
# t.me/avitostata_bot           DEVELOPMENT
# t.me/avitostata_ru_bot        PRODUCTION

ENVIRONMENT = os.getenv('ENVIRONMENT')
if ENVIRONMENT == 'PRODUCTION':
    bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN_PROD'))
else:
    bot = Bot(os.getenv('TELEGRAM_BOT_TOKEN'))

dp = Dispatcher()
logging.basicConfig(level=logging.INFO)
router = Router()
scheduler = AsyncIOScheduler()  # Автоматическая отправка сообщений


async def trigger_error():
    division_by_zero = 1 / 0


# async def scheduler_setup(scheduler: AsyncIOScheduler):
#     moscow_tz = pytz.timezone('Europe/Moscow')
#     scheduler.add_job(
#         send_text_report_all,
#         'cron',
#         day_of_week='mon',
#         hour=13,
#         minute=0,
#         timezone=moscow_tz
#     )
#     scheduler.start()



@router.message()
async def echo(message: Message, bot: Bot):
    msg = message.text.lower()

    if message.from_user.id == 5640395403:
        if msg == "/pdf_all_to_users@avitostata_bot":
            # TODO check error when you tap on command
            await get_pdf_report_all_to_users()
        if msg == "/pdf_all_to_admin@avitostata_bot":
            await get_pdf_report_all_to_admin()

        if msg == "/sentry_log@avitostata_bot":
            await trigger_error()

        if msg in ["/help@avitostata_bot", "/help", "help"]:
            await message.reply(
                "\nТЕСТИРОВАНИЕ С ПРОДА \n"
                "/pdf_all_to_admin@avitostata_bot - пдф все админу \n"
                "/sentry_log - пробная ошибка на сентри \n"

                
                "\nЮЗЕРАМ\n"
                "/pdf_all_to_users@avitostata_bot - отчёт ПДФ всем \n"
            )

        else:
            pass


async def main() -> None:
    dp.include_router(router)

    cleaner = Cleaner(limit=100)
    dp.update.middleware(CleanerMiddleware(cleaner))

    # await scheduler_setup(scheduler)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
