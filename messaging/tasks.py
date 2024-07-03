import os
import shutil

from celery import shared_task
from asgiref.sync import async_to_sync, sync_to_async
from avito_account.models import AvitoAccount
from messaging.utils_bad_messaging_report import get_bad_messaging_week_report_pdf
from telegram_bot import bot


@shared_task
def send_test_message():
    async_to_sync(_send_test_message_async)()


async def _send_test_message_async():
    all_avito_accounts = await sync_to_async(list)(
        AvitoAccount.objects.filter(company__is_active=True, telegram_id__isnull=False)
    )
    for avito_account in all_avito_accounts:
        pdf_path = await get_bad_messaging_week_report_pdf(avito_account.id)
        await sync_to_async(bot.send_raw, thread_sensitive=False)(chat_id=avito_account.telegram_id,
                                                                  text=f"TEST TEXT. PDF Path: {pdf_path}")


@shared_task
def clean_up_folder_task():
    async_to_sync(clean_up_folder)('reports/bad_messaging_reports')


async def clean_up_folder(folder_path):
    await sync_to_async(shutil.rmtree)(folder_path)
    os.makedirs(folder_path)
