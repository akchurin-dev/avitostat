from celery import shared_task
from telegram_bot import bot

from avito_account.models import AvitoAccount
from messaging.utils_bad_messaging_report import get_bad_messaging_week_report_pdf


@shared_task
def send_test_message():
    # pdf = await get_bad_messaging_week_report_pdf(84804440)
    all_avito_accounts = AvitoAccount.objects.filter(company__is_active=True, telegram_id__isnull=False)
    for avito_account in all_avito_accounts:
        bot.send_raw(chat_id=avito_account.telegram_id, text="TEST TEXT")
