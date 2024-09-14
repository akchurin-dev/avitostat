import os
import shutil
import sentry_sdk
from celery import shared_task
from asgiref.sync import async_to_sync, sync_to_async
from django.utils import timezone
from avito_account.models import AvitoAccount, SendingCampaign, SendingReport
from telegram_bot import bot
from aiogram import types
from base.celery import celery_app
from messaging.bad_mes_report.utils_bad_messaging_report import get_messaging_week_report_pdf


@celery_app.task(name='messaging.tasks.bad_messaging_week_report_async_task')
def bad_messaging_week_report_async_task(only_for_users=None, test_from_prod=False):
    async_to_sync(bad_messaging_week_report_async)(only_for_users=only_for_users, test_from_prod=test_from_prod)


async def bad_messaging_week_report_async(test_from_prod: bool = False, only_for_users=None):
    # Queryset filtering logic
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

    # DEVELOPMENT testing checking
    ENVIRONMENT = os.getenv('ENVIRONMENT')
    if ENVIRONMENT == 'DEVELOPMENT':
        test_from_prod = True

    # Create a new SendingCampaign
    campaign = await SendingCampaign.objects.acreate(
        name="weekly",
        test_from_prod=test_from_prod,
        sending_type=SendingCampaign.PDF,
        created_at=timezone.now(),
        accounts_presented_count=len(all_avito_accounts),
    )
    await sync_to_async(campaign.accounts_presented.add)(*all_avito_accounts)


    # CORE logic
    for avito_account in all_avito_accounts:
        print(avito_account.name)
        pdf_path = None
        try:
            pdf_path = await get_messaging_week_report_pdf(avito_account.id, test_from_prod)
            if pdf_path:
                chat_id = "-4221870448" if test_from_prod else avito_account.telegram_id
                try:
                    await sync_to_async(bot.send_raw, thread_sensitive=False)(
                        chat_id=chat_id,
                        function="send_document",
                        document=types.FSInputFile(pdf_path))
                    success = True
                    error_message = None
                except Exception as send_error:
                    sentry_sdk.capture_exception(send_error)
                    print(send_error)
                    success = False
                    error_message = str(send_error)[:255]
            else:
                success = False
                error_message = "Failed to generate PDF"
        except Exception as e:
            sentry_sdk.capture_exception(e)
            print(e)
            success = False
            error_message = str(e)[:255]

        # Save SendingReport
        await SendingReport.objects.acreate(
            avito_account=avito_account,
            campaign=campaign,
            success=success,
            error_message=error_message,
            pdf_path=pdf_path,
            timestamp=timezone.now()
        )


@shared_task
def bad_mes_report_pdfs_folder_cleaner_task():
    async_to_sync(bad_mes_report_pdfs_folder_cleaner)('messaging/bad_mes_report/PDFs')


async def bad_mes_report_pdfs_folder_cleaner(folder_path):
    await sync_to_async(shutil.rmtree)(folder_path)
    os.makedirs(folder_path)
