import os
from asgiref.sync import async_to_sync, sync_to_async
from django.utils import timezone
from telegram_bot import bot
from avito_account.models import SendingCampaign, AvitoAccount, SendingReport
from base.celery import celery_app
from conversion.utils_from_aiogram import get_week_report_text, get_avito_account_all_ids


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
    campaign = await SendingCampaign.objects.acreate(
        name='weekly',
        test_from_prod=test_from_prod,
        sending_type=SendingCampaign.TEXT,
        created_at=timezone.now(),
    )

    if only_for_users is not None:
        avito_account_ids = only_for_users
    else:
        avito_account_ids = await get_avito_account_all_ids()

    # queryset = await sync_to_async(AvitoAccount.objects.filter)(id__in=avito_account_ids)
    for account_id in avito_account_ids:
        avito_account = await AvitoAccount.objects.aget(telegram_id=account_id)
        try:
            await send_txt_week_report_individual_async(int(account_id), test_from_prod=test_from_prod)
            await SendingReport.objects.acreate(
                avito_account=avito_account,
                campaign=campaign,
                success=True,
                pdf_path=None,
                timestamp=timezone.now()
            )
        except Exception as e:
            await SendingReport.objects.acreate(
                avito_account=avito_account,
                campaign=campaign,
                success=False,
                error_message=str(e)[:50],
                timestamp=timezone.now(),
                pdf_path=None
            )
