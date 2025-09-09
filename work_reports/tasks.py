from datetime import datetime
from datetime import timedelta

from aiogram import Bot
from celery import shared_task

from base.settings import AVITOSTATA_ALIVE_BOT_TOKEN
from base.settings import AVITOSTATA_ALIVE_REPORTS_CHAT_ID
from utils.logging import TraceLogger
from utils.miscellaneous import datetime_now_msk
from utils.tg import send_message
from work_reports import daily_report
from work_reports import monthly_report
from work_reports import weekly_report


reports_bot = Bot(token=AVITOSTATA_ALIVE_BOT_TOKEN)


@shared_task
def send_daily_report() -> None:
    today_date = datetime_now_msk().date()
    until = datetime.combine(today_date, datetime.min.time()) - timedelta(hours=3)
    since = until - timedelta(days=1)
    report = daily_report.make_daily_report(since, until)
    yestarday_date = today_date - timedelta(days=1)
    text = daily_report.form_daily_report_message_text(yestarday_date, report)
    send_message(AVITOSTATA_ALIVE_REPORTS_CHAT_ID, text, bot=reports_bot)


@shared_task
def send_weekly_report() -> None:
    last_juma = datetime_now_msk().date()
    while last_juma.weekday() != 4:
        last_juma -= timedelta(days=1)

    until = datetime.combine(datetime_now_msk().date(), datetime.min.time()) - timedelta(hours=3)
    since = until - timedelta(days=7)
    report = weekly_report.make_weekly_report(since, until, last_juma)
    text = weekly_report.get_weekly_report_message_text(report)
    send_message(AVITOSTATA_ALIVE_REPORTS_CHAT_ID, text, bot=reports_bot)


@shared_task
def send_report_for_last_30_days() -> None:
    until = datetime.combine(datetime_now_msk().date(), datetime.min.time()) - timedelta(hours=3)
    since = until - timedelta(days=30)
    report = monthly_report.make_monthly_report(since, until)
    text = monthly_report.get_monthly_report_message_text(since, until, report)
    send_message(AVITOSTATA_ALIVE_REPORTS_CHAT_ID, text, bot=reports_bot)
