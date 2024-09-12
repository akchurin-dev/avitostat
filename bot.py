import asyncio
import logging
import os
import sys
import pytz

import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.types import Message
from dotenv import load_dotenv

from bot.week_report import get_week_report_text
from tg_bot.api.week_report import get_avito_account_all_ids, get_pdf_report_all_to_users, \
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


async def scheduler_setup(scheduler: AsyncIOScheduler):
    moscow_tz = pytz.timezone('Europe/Moscow')
    scheduler.add_job(
        send_text_report_all,
        'cron',
        day_of_week='mon',
        hour=13,
        minute=0,
        timezone=moscow_tz
    )
    scheduler.start()


async def send_text_report_all(test_from_prod: bool = False):
    avito_account_ids = get_avito_account_all_ids()
    if avito_account_ids:
        for account_id in avito_account_ids:
            await send_week_report(int(account_id), test_from_prod=test_from_prod)


async def send_week_report(telegram_chat_id: int, test_from_prod: bool = False):
    text = await get_week_report_text(telegram_chat_id, bot=bot)

    ENVIRONMENT = os.getenv('ENVIRONMENT')
    if ENVIRONMENT == 'DEVELOPMENT' or test_from_prod:
        chat_id = "-4221870448"
    else:
        chat_id = telegram_chat_id

    while text:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        text = text[4000:]


@router.message()
async def echo(message: Message, bot: Bot):
    msg = message.text.lower()

    # TODO ПЕРЕНЕСТИ на ДЖАНГО
    if msg == "/week@avitostata_bot":
        await send_week_report(message.chat.id)
    if message.from_user.id == 5640395403:
        if msg == "/text_report_all_users@avitostata_bot":
            await send_text_report_all()
        if msg == "/text_report_all_admin@avitostata_bot":
            await send_text_report_all(test_from_prod=True)

        # TODO ПЕРЕНОСИТЬ НЕНУЖНО
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
                "/text_report_all_admin@avitostata_bot - текстовый все аккаунты админу \n"
                "/pdf_all_to_admin@avitostata_bot - пдф все админу \n"
                "/sentry_log - пробная ошибка на сентри \n"

                
                "\nЮЗЕРАМ\n"
                "/week@avitostata_bot - отчёт текстовый индивидуально \n"
                "/text_report_all_users@avitostata_bot - отчёт текстовый юзерам \n"
                "/pdf_all_to_users@avitostata_bot - отчёт ПДФ всем \n"
            )

        else:
            pass


async def main() -> None:
    dp.include_router(router)

    cleaner = Cleaner(limit=100)
    dp.update.middleware(CleanerMiddleware(cleaner))

    await scheduler_setup(scheduler)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
