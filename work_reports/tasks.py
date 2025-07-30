from datetime import timedelta

from aiogram import Bot
from celery import shared_task

from base.settings import AVITOSTATA_ALIVE_BOT_TOKEN
from base.settings import AVITOSTATA_ALIVE_REPORTS_CHAT_ID
from utils.logging import TraceLogger
from utils.miscellaneous import datetime_now_msk
from utils.tg import send_message
from work_reports import daily_report


reports_bot = Bot(token=AVITOSTATA_ALIVE_BOT_TOKEN)


@shared_task
def send_daily_report():
    until = datetime_now_msk()
    since = until - timedelta(days=1)
    report = daily_report.make_daily_report(since, until)
    text = daily_report.form_daily_report_message_text(f"Отчет за {until.strftime('%d.%m')} по ИИ-продавцу", report)
    send_message(AVITOSTATA_ALIVE_REPORTS_CHAT_ID, text, bot=reports_bot)


@shared_task
def weekly_report():
    pass
