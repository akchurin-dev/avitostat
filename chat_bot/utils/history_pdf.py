import datetime

from asgiref.sync import async_to_sync
from celery import shared_task
from jinja2 import Template

from avito_account.models.models import AvitoAccount
from chat_bot.models import ChatBotTask
from chat_bot.utils import pdf_report
from messaging.bad_mes_report.utils_bad_messaging_report import chats_timestamp_to_datetime
from utils import tg
from utils.logging import TraceLogger


@shared_task
def history_pdf_sender_task(
    avito_account_id,
    chat,
    summary_html: str | None = None,
    telegram_id: str | None = None,
    *,
    trace_id: str | None = None,
) -> None:

    tlogger = TraceLogger(trace_id)
    tlogger.info("History pdf sending is started")

    add_from_bot_flag(chat)
    async_to_sync(chats_timestamp_to_datetime)({"chats": [chat]})
    avito_account = AvitoAccount.objects.get(id=avito_account_id)
    statistics = {"avito_account_name": avito_account.name, "avito_account_id": avito_account.pk, }
    html_content = get_history_html(
        chat=chat,
        statistics=statistics,
        summary_html=summary_html,
    )
    report_name_prefix = f"history_{avito_account.name}"
    pdf_path = pdf_report.get_pdf(statistics, html_content, report_name_prefix)
    if pdf_path is not None:
        telegram_id = telegram_id or avito_account.telegram_id
        assert telegram_id is not None
        # ChatBotSummaryReportClass.file_sender_to_tg(pdf_path, telegram_id)
        tg.send_document(telegram_id, pdf_path)

    tlogger.info("History pdf sending is finished")


def add_from_bot_flag(chat):
    chat_bot_tasks = ChatBotTask.objects.filter(chat_id=chat.get("id"), tokens_completion__gt=0)
    bot_answered_mes_ids = list(chat_bot_tasks.values_list("message_id", flat=True).distinct())

    set_from_bot_next = False  # Флаг для следующей итерации
    for message in chat.get("messages", []):
        if set_from_bot_next:
            message["from_bot"] = True
            set_from_bot_next = False  # Сбрасываем флаг
        else:
            message["from_bot"] = False
        if message.get("id") in bot_answered_mes_ids:
            set_from_bot_next = True  # Активируем флаг для следующей итерации
    return chat


def get_history_html(chat, statistics, summary_html = None):
    with open(f"chat_bot/templates/chat_bot/ai_chatting_history.html", "r", encoding="utf-8") as file:
        clear_template = file.read()

    template = Template(clear_template)
    avito_account_name = statistics.get('avito_account_name') if statistics else "Неизвестно"
    date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    client_name = chat.get("users")[0].get("name")

    return template.render(
        avito_account_name=avito_account_name,
        client_name=client_name,
        start_date=date,
        chat=chat,
        summary_html=summary_html,
    )
