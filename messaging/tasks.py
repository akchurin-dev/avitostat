import shutil
import sentry_sdk
from celery import shared_task
from asgiref.sync import async_to_sync, sync_to_async
from django.utils import timezone
from avito_account.models.models import AvitoAccount
from telegram_bot import bot
from aiogram import types
from avito_account.models.sending_report import SendingCampaign, SendingReport
from base import settings
from base.celery import celery_app
from messaging.bad_mes_report.utils_bad_messaging_report import get_messaging_week_report_pdf
import subprocess
import os
from datetime import datetime
from payments.utils import waste_of_balance, check_balance


@celery_app.task(name='messaging.tasks.db_backup_auto_creator_task')
def db_backup_auto_creator_task():
    db_host = settings.DB_HOST
    db_port = settings.DB_PORT
    db_user = settings.DB_USER
    db_name = settings.DB_NAME
    db_password = settings.DB_PASS
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


@celery_app.task(name='messaging.tasks.bad_messaging_week_report_async_task')
def bad_messaging_week_report_async_task(only_for_users=None, test_from_prod=False):
    async_to_sync(bad_messaging_week_report_async)(only_for_users=only_for_users, test_from_prod=test_from_prod)


@celery_app.task(name='messaging.tasks.bad_messaging_week_report_async_task_auto_generated')
def bad_messaging_week_report_async_task_auto_generated(only_for_users=None, test_from_prod=False, auto_generated=True):
    async_to_sync(bad_messaging_week_report_async)(only_for_users=only_for_users, test_from_prod=test_from_prod,
                                                   auto_generated=auto_generated)


async def get_account_for_pdf_reports(only_for_users: list, test_from_prod: bool):
    if only_for_users is None:
        all_avito_accounts = await sync_to_async(list)(AvitoAccount.objects.filter(
            created_by__is_active=True,
            telegram_id__isnull=False))
    else:
        all_avito_accounts = await sync_to_async(list)(AvitoAccount.objects.filter(
            created_by__is_active=True,
            telegram_id__isnull=False,
            id__in=only_for_users, ))

        # Create a new SendingCampaign
    campaign = await SendingCampaign.objects.acreate(
        name="weekly",
        test_from_prod=test_from_prod,
        sending_type=SendingCampaign.PDF,
        created_at=timezone.now(),
        accounts_presented_count=len(all_avito_accounts),
    )
    await sync_to_async(campaign.accounts_presented.add)(*all_avito_accounts)
    return all_avito_accounts, campaign



# TODO change auto_generated=False by default
async def bad_messaging_week_report_async(only_for_users=None, test_from_prod: bool = True, auto_generated=True):
    if settings.ENVIRONMENT == 'DEVELOPMENT':
        test_from_prod = False

    all_avito_accounts, campaign = await get_account_for_pdf_reports(only_for_users=only_for_users,
                                                                     test_from_prod=test_from_prod)

    if len(all_avito_accounts) == 0:
        return None

    # CORE logic
    for avito_account in all_avito_accounts:
        print(avito_account.name)
        pdf_path = None
        balance_decrease = 0
        tokens = {"completion": -99, "prompt": -99}  # default values
        try:
            await check_balance(avito_account)
            pdf_path, tokens = await get_messaging_week_report_pdf(avito_account.id, test_from_prod)
            if pdf_path:
                chat_id = "-4221870448" if test_from_prod else avito_account.telegram_id
                try:
                    await sync_to_async(bot.send_raw, thread_sensitive=False)(
                        chat_id=chat_id,
                        function="send_document",
                        document=types.FSInputFile(pdf_path))
                    success = True
                    error_message = None
                    print(auto_generated, test_from_prod)
                    if auto_generated:
                        campaign.auto_generated = True
                        await campaign.asave()
                        if not test_from_prod:
                            balance_decrease = 500
                            await waste_of_balance(avito_account, balance_decrease)

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

        await SendingReport.objects.acreate(
            avito_account=avito_account, campaign=campaign, success=success, balance_decrease=balance_decrease,
            error_message=error_message, pdf_path=pdf_path, timestamp=timezone.now(),
            tokens_completion=tokens.get("completion"), tokens_prompt=tokens.get("prompt"),
        )


@shared_task
def bad_mes_report_pdfs_folder_cleaner_task():
    async_to_sync(bad_mes_report_pdfs_folder_cleaner)('messaging/bad_mes_report/PDFs')


async def bad_mes_report_pdfs_folder_cleaner(folder_path):
    await sync_to_async(shutil.rmtree)(folder_path)
    os.makedirs(folder_path)
