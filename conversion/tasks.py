import os
from asgiref.sync import async_to_sync, sync_to_async
from django.utils import timezone
from telegram_bot import bot

from avito_account.models import SendingCampaign, SendingReport, AvitoAccount
from base.celery import celery_app
from conversion.utils_from_aiogram import get_week_report_text


async def send_txt_week_report_individual_async(avito_account: AvitoAccount, test_from_prod: bool = False):
    text = await get_week_report_text(avito_account)

    ENVIRONMENT = os.getenv('ENVIRONMENT')
    if ENVIRONMENT == 'DEVELOPMENT' or test_from_prod:
        chat_id = "-4221870448"
    else:
        chat_id = avito_account.telegram_id

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
    ENVIRONMENT = os.getenv('ENVIRONMENT')
    if ENVIRONMENT == 'DEVELOPMENT':
        test_from_prod = True

    campaign = await SendingCampaign.objects.acreate(
        name='weekly',
        test_from_prod=test_from_prod,
        sending_type=SendingCampaign.TEXT,
        created_at=timezone.now(),
    )

    if only_for_users is not None:
        avito_accounts = await sync_to_async(list)(AvitoAccount.objects.filter(id__in=only_for_users, company__is_active=True))
    else:
        avito_accounts = await sync_to_async(list)(AvitoAccount.objects.filter(company__is_active=True))

    for avito_account in avito_accounts:
        print(avito_account.name)
        try:
            await send_txt_week_report_individual_async(avito_account, test_from_prod=test_from_prod)
            success = True
            error_message = None

        except Exception as e:
            success = False
            error_message = str(e)[:50]
            print(e)

        await SendingReport.objects.acreate(
            avito_account=avito_account,
            campaign=campaign,
            success=success,
            error_message=error_message,
            timestamp=timezone.now(),
            pdf_path=None
        )
