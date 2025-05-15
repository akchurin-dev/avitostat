from asgiref.sync import async_to_sync, sync_to_async
from django.utils import timezone
from telegram_bot import bot

from avito_account.models.models import AvitoAccount
from avito_account.models.sending_report import SendingCampaign, SendingReport
from base import settings
from base.celery import celery_app
from celery import shared_task
from conversion.utils_from_aiogram import get_week_report_text
import payments.utils as payments
from utils.logging import TraceLogger


async def send_txt_week_report_individual_async(avito_account: AvitoAccount, test_from_prod: bool = False):
    text = await get_week_report_text(avito_account)

    if settings.ENVIRONMENT == 'DEVELOPMENT' or test_from_prod:
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


@celery_app.task(name='conversion.tasks.send_text_report_all_async_task_auto_generated')
def send_text_report_all_async_task_auto_generated(test_from_prod=False, only_for_users=None, auto_generated=True):
    async_to_sync(send_text_report_all_async)(test_from_prod=test_from_prod, only_for_users=only_for_users, auto_generated=auto_generated)


async def send_text_report_all_async(
    test_from_prod: bool = False,
    only_for_users: list[int] | None = None,
    auto_generated=False,
):
    tlogger = TraceLogger()
    tlogger.info("Weekly text report sending started")

    if settings.ENVIRONMENT == 'DEVELOPMENT':
        test_from_prod = True

    avito_accounts_qs = AvitoAccount.objects.filter(created_by__is_active=True)

    if only_for_users:
        avito_accounts_qs = avito_accounts_qs.filter(id__in=only_for_users)

    avito_accounts = [account async for account in avito_accounts_qs]

    tlogger.info(f"Accounts for text report: {[account.name for account in avito_accounts]}")

    campaign = await SendingCampaign.objects.acreate(
        name='weekly',
        test_from_prod=test_from_prod,
        sending_type=SendingCampaign.TEXT,
        created_at=timezone.now(),
        accounts_presented_count=len(avito_accounts),
        auto_generated=auto_generated
    )
    await campaign.accounts_presented.aadd(*avito_accounts)

    for avito_account in avito_accounts:
        send_report_for_account.delay(avito_account.pk, campaign.pk, auto_generated, test_from_prod)


@shared_task
def send_report_for_account(account_id: int, campaign_id: int, auto_generated: bool, test_from_prod: bool):
    account = AvitoAccount.objects.get(pk=account_id)

    async def f():
        tlogger = TraceLogger()
        tlogger.info(f"Start report sending for '{account.name}'")

        success = True
        error_message = None

        try:
            await payments.check_balance_enought(
                user=account.created_by,
                required_amount=payments.REPORT_DEFAULT_COST,
            )
            await send_txt_week_report_individual_async(account, test_from_prod=test_from_prod)

            if auto_generated:
                await SendingCampaign.objects.filter(pk=campaign_id).aupdate(auto_generated=True)

        except Exception as e:
            tlogger.warning(e)

            success = False
            error_message = str(e)[:255]

            raise

        finally:
            await SendingReport.objects.acreate(
                avito_account=account,
                campaign_id=campaign_id,
                success=success,
                error_message=error_message,
                timestamp=timezone.now(),
                pdf_path=None
            )

    async_to_sync(f)()
