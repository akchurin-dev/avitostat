import os
from asgiref.sync import async_to_sync, sync_to_async
from telegram_bot import bot
from base.celery import celery_app
from conversion.utils_from_aiogram import get_week_report_text, get_avito_account_all_ids
from exceptions import HTTPException


# @celery_app.task(name='conversion.tasks.send_txt_week_report_individual_async')
# def send_txt_week_report_individual_async_task(telegram_chat_id=None, test_from_prod=False):
#     async_to_sync(send_txt_week_report_individual_async)(telegram_chat_id=telegram_chat_id, test_from_prod=test_from_prod)


async def send_txt_week_report_individual_async(telegram_chat_id: int, test_from_prod: bool = False):
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


@celery_app.task(name='conversion.tasks.send_text_report_all_async_task')
def send_text_report_all_async_task(test_from_prod=False, only_for_users=None):
    async_to_sync(send_text_report_all_async)(test_from_prod=test_from_prod, only_for_users=only_for_users)


async def send_text_report_all_async(test_from_prod: bool = False, only_for_users=None):
    if only_for_users is not None:
        avito_account_ids = only_for_users
    else:
        avito_account_ids = await get_avito_account_all_ids()
    for account_id in avito_account_ids:
        try:
            await send_txt_week_report_individual_async(int(account_id), test_from_prod=test_from_prod)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
