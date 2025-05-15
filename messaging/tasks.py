from datetime import datetime
import os

from aiogram import types
from asgiref.sync import async_to_sync, sync_to_async
from celery import shared_task
from django.utils import timezone
from pathlib import Path
import shutil
import sentry_sdk
import subprocess

from avito_account.models.models import AvitoAccount
from avito_account.models.sending_report import SendingCampaign, SendingReport
from base import settings
from base.celery import celery_app
from messaging.bad_mes_report.utils_bad_messaging_report import get_messaging_report_data
import payments.utils as payment
from utils import tg
from utils.logging import TraceLogger


@celery_app.task(name='messaging.tasks.get_messaging_report_data')
def get_messaging_report_data_async_task(test_from_prod: bool, avito_account_id,
                                         for_api: bool = False, period: str = "week"):
    async_to_sync(get_messaging_report_data)(
        test_from_prod=test_from_prod,
        avito_account_id=avito_account_id,
        for_api=for_api,
        period=period,
        tlogger=TraceLogger(),
    )


@celery_app.task(name='messaging.tasks.month_report_json_getting')
def month_report_json_getting_async_task():
    all_avito_accounts = AvitoAccount.objects.filter(created_by__is_active=True)
    for avito_account in all_avito_accounts:
        get_messaging_report_data_async_task.delay(
            test_from_prod=False,
            avito_account_id=avito_account.pk,
            for_api=True,
            period="month"
        )


@celery_app.task(name='messaging.tasks.bad_messaging_week_report_async_task')
def bad_messaging_week_report_async_task(only_for_users: list[int] | None = None, test_from_prod=False, period: str = "week"):
    async_to_sync(bad_messaging_report_by_period)(
        only_for_users=only_for_users,
        test_from_prod=test_from_prod,
        period=period,
    )


@celery_app.task(name='messaging.tasks.bad_messaging_week_report_async_task_auto_generated')
def bad_messaging_week_report_async_task_auto_generated(only_for_users: list[int] | None = None, test_from_prod=False, auto_generated=True):
    async_to_sync(bad_messaging_report_by_period)(
        only_for_users=only_for_users,
        test_from_prod=test_from_prod,
        auto_generated=auto_generated,
    )


async def get_accounts_for_pdf_reports(only_for_users: list[int] | None, test_from_prod: bool):
    all_avito_accounts_qs = AvitoAccount.objects.filter(
        created_by__is_active=True,
        telegram_id__isnull=False,
    ).select_related("created_by")

    if only_for_users:
        all_avito_accounts_qs = all_avito_accounts_qs.filter(id__in=only_for_users)

    all_avito_accounts = [account async for account in all_avito_accounts_qs]

    campaign = await SendingCampaign.objects.acreate(
        name="weekly",
        test_from_prod=test_from_prod,
        sending_type=SendingCampaign.PDF,
        created_at=timezone.now(),
        accounts_presented_count=len(all_avito_accounts),
    )

    await campaign.accounts_presented.aadd(*all_avito_accounts_qs)

    return all_avito_accounts, campaign


# TODO change auto_generated=False by default
async def bad_messaging_report_by_period(
    only_for_users: list[int] | None = None,
    test_from_prod: bool = True,
    auto_generated=True,
    pdf_path=None,
    balance_decrease=0,
    period: str = "week",
):
    tlogger = TraceLogger()
    tlogger.info(f"Bad messaging report for {period} is started")

    # TODO change test_from_prod=True
    if settings.ENVIRONMENT == 'DEVELOPMENT':
        test_from_prod = True

    accounts, campaign = await get_accounts_for_pdf_reports(
        only_for_users=only_for_users,
        test_from_prod=test_from_prod,
    )

    tlogger.info(f"Accounts for report: {[account.name for account in accounts]}")

    for account in accounts:
        bad_messaging_report_by_period_for_account.delay(account.pk, campaign.pk, period, test_from_prod, auto_generated, pdf_path)


@shared_task
def bad_messaging_report_by_period_for_account(
    account_id: int,
    campaign_id: int,
    period: str,
    test_from_prod: bool,
    auto_generated: bool,
    pdf_path: str | Path | None = None,
):
    account = AvitoAccount.objects.filter(pk=account_id).select_related("created_by").get()
    campaign = SendingCampaign.objects.get(pk=campaign_id)

    async def f():
        nonlocal pdf_path

        tlogger = TraceLogger()
        tlogger.info(f"Start report sending for '{account.name}'")

        tokens = {"completion": -99, "prompt": -99}

        try:
            if not account.telegram_id:
                error = "telegram_id isn't valid"
                tlogger.info(error)
                raise Exception(error)

            report_cost = payment.REPORT_DEFAULT_COST
            if test_from_prod:
                report_cost = 0

            await payment.check_balance_enought(
                user=account.created_by,
                required_amount=payment.REPORT_DEFAULT_COST,
            )

            messaging_report = await get_messaging_report_data(
                avito_account_id=account.pk,
                test_from_prod=test_from_prod,
                period=period,
                tlogger=tlogger,
            )

            if messaging_report is None:
                raise Exception("Messaging report is None")

            pdf_path = messaging_report.pdf_path

            if messaging_report.tokens:
                tokens = messaging_report.tokens

            await tg.asend_document(account.telegram_id, pdf_path)

            success = True
            error_message = None

            if auto_generated:
                campaign.auto_generated = True
                await campaign.asave()
                await payment.waste_of_balance(
                    user=account.created_by,
                    balance_decrease=report_cost,
                )
        except Exception as e:
            sentry_sdk.capture_exception(e)
            tlogger.warning(e)
            success = False
            error_message = str(e)[:255]
            raise
        finally:
            await SendingReport.objects.acreate(
                avito_account=account,
                campaign=campaign,
                success=success,
                balance_decrease=report_cost,
                error_message=error_message,
                pdf_path=pdf_path,
                timestamp=timezone.now(),
                tokens_completion=tokens.get("completion"),
                tokens_prompt=tokens.get("prompt"),
            )

    async_to_sync(f)()


@shared_task
def bad_mes_report_pdfs_folder_cleaner_task():
    async_to_sync(bad_mes_report_pdfs_folder_cleaner)('messaging/bad_mes_report/PDFs')


async def bad_mes_report_pdfs_folder_cleaner(folder_path):
    await sync_to_async(shutil.rmtree)(folder_path)
    os.makedirs(folder_path)


@celery_app.task(name='messaging.tasks.db_backup_auto_creator_task')
def db_backup_auto_creator_task():
    db_host = settings.DB_HOST
    db_port = settings.DB_PORT
    db_user = settings.DB_USER
    db_name = settings.DB_NAME
    db_password = settings.DB_PASS
    assert db_password is not None
    backup_dir = '/var/backups/db_backups'
    backup_filename = f"local_db_dump_{datetime.now().strftime('%Y-%m-%d')}.sql"

    command = [
        'pg_dump',
        '-h', db_host,
        '-p', db_port,
        '-U', db_user,
        '-d', db_name,
        '-F', 'c',
        '-f', os.path.join(backup_dir, backup_filename)
    ]

    # Установка переменной окружения для пароля
    env = os.environ.copy()
    env['PGPASSWORD'] = db_password

    # Выполнение команды
    try:
        subprocess.run(command, env=env, check=True)
        print(f"Backup successful: {backup_filename}")
    except subprocess.CalledProcessError as e:
        print(f"Error during backup: {e}")
