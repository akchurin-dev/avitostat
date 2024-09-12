import os
from asgiref.sync import async_to_sync, sync_to_async
from telegram_bot import bot
from base.celery import celery_app
from conversion.utils_from_aiogram import get_week_report_text


@celery_app.task(name='conversion.tasks.bad_messaging_week_report_async_task')
def send_txt_week_report_async_task(telegram_chat_id=None, test_from_prod=False):
    async_to_sync(send_txt_week_report_async)(telegram_chat_id=telegram_chat_id, test_from_prod=test_from_prod)


async def send_txt_week_report_async(telegram_chat_id: int, test_from_prod: bool = False):
    text = await get_week_report_text(telegram_chat_id)

    ENVIRONMENT = os.getenv('ENVIRONMENT')
    if ENVIRONMENT == 'DEVELOPMENT' or test_from_prod:
        chat_id = "-4221870448"
    else:
        chat_id = telegram_chat_id

    while text:
        await sync_to_async(bot.send_raw, thread_sensitive=False)(
            chat_id=chat_id,
            function="send_message",
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        text = text[4000:]
