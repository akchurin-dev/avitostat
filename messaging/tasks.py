import os
import shutil
import sentry_sdk
from celery import shared_task
from asgiref.sync import async_to_sync, sync_to_async

from avito_account.models import AvitoAccount
from telegram_bot import bot
from aiogram import types

from base.celery import celery_app
from messaging.bad_mes_report.utils_bad_messaging_report import get_messaging_week_report_pdf


@celery_app.task(name='messaging.tasks.bad_messaging_week_report_async_task')
def bad_messaging_week_report_async_task(only_for_users=None):
    async_to_sync(bad_messaging_week_report_async)(only_for_users=only_for_users)


async def bad_messaging_week_report_async(test_from_prod: bool = False, only_for_users=None):
    #  Queryset filtering logic
    if only_for_users is None:
        all_avito_accounts = await sync_to_async(list)(AvitoAccount.objects.filter(
            company__is_active=True,
            telegram_id__isnull=False))
    else:
        all_avito_accounts = await sync_to_async(list)(AvitoAccount.objects.filter(
            id__in=only_for_users,
            company__is_active=True,
            telegram_id__isnull=False))
        if len(all_avito_accounts) == 0:
            return None

    # DEVELOPEMENT testing checking
    ENVIRONMENT = os.getenv('ENVIRONMENT')
    if ENVIRONMENT == 'DEVELOPMENT':
        test_from_prod = True

    # CORE logic
    for avito_account in all_avito_accounts:
        try:
            pdf_path = await get_messaging_week_report_pdf(avito_account.id, test_from_prod)
            if pdf_path:
                chat_id = "-4221870448" if test_from_prod else avito_account.telegram_id

                try:
                    await sync_to_async(bot.send_raw, thread_sensitive=False)(
                        chat_id=chat_id,
                        function="send_document",
                        document=types.FSInputFile(pdf_path))
                    # return True

                except Exception as send_error:
                    sentry_sdk.capture_exception(send_error)
                    print(send_error)
        except Exception as e:
            sentry_sdk.capture_exception(e)  # Отправка исключения в Sentry
            print(e)
            # raise e


@shared_task
def bad_mes_report_pdfs_folder_cleaner_task():
    async_to_sync(bad_mes_report_pdfs_folder_cleaner)('messaging/bad_mes_report/PDFs')


async def bad_mes_report_pdfs_folder_cleaner(folder_path):
    await sync_to_async(shutil.rmtree)(folder_path)
    os.makedirs(folder_path)
