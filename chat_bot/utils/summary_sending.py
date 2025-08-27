from asgiref.sync import async_to_sync
from django.db.models import QuerySet

import messaging.api
from avito_account.models.models import AvitoAccount
from base import settings
from chat_bot import ai_utils
from chat_bot.models import ChatBotTask
from chat_bot.utils import history_pdf
from chat_bot.utils import summaries
from utils import tg
from utils.logging import TraceLogger


def send_summary(account: AvitoAccount, chat_id, *, trace_id: str | None = None):
    tlogger = TraceLogger(trace_id)

    all_tasks = ChatBotTask.objects.filter(chat_id=chat_id)

    if summaries.new_contact_report_sent(account, chat_id):
        tlogger.info(f"Stop summary sending. Summary report already sent for chat_id {chat_id}.")
        return

    messages = messaging.api.get_chat_last_50_messages_by_chat_id(account, chat_id, tlogger=tlogger).get("messages")

    if not messages:
        tlogger.info("Stop summary sending. No messages in chat")
        return

    chat = messaging.api.get_chat_by_id(account, chat_id, tlogger=tlogger)
    chat["messages"] = messages

    chat_summary = ai_utils.avito_chat_summary_ai_generator(account, chat_id, tlogger=tlogger)
    if chat_summary:
        summary_sender(account, chat_summary, chat, all_tasks, tlogger=tlogger)
    else:
        tlogger.info(f"Chat summary is empty, got {chat_summary}")


def summary_sender(
    avito_account: AvitoAccount,
    chat_summary: ai_utils.ChatSummary,
    chat: messaging.api.Chat,
    all_tasks: QuerySet[ChatBotTask],
    *,
    tlogger: TraceLogger,
):
    summary_text = get_chat_summary_text(chat_summary, chat)
    tlogger.info(f"Summary report summary_text {summary_text}.")

    telegram_id = avito_account.telegram_id
    location = "Location not defined"

    task_with_company_branch = all_tasks.filter(company_branch__isnull=False).order_by("created_at").last()
    if task_with_company_branch:
        assert task_with_company_branch.company_branch
        telegram_id = task_with_company_branch.company_branch.telegram_id
        location = task_with_company_branch.company_branch.location

    if telegram_id is None:
        error = "telegram_id is None"
        tlogger.error(error)
        raise Exception(error)

    if summary_text and len(summary_text) > 20:  # 20 is random value)
        tlogger.info(f"Send summary report to chat (tg_id={telegram_id}) of '{avito_account.name}' ({location})")
        # ChatBotSummaryReportClass.text_sender_to_tg(text=summary_text, telegram_id=telegram_id)
        tg.send_message(telegram_id, summary_text)
        tlogger.info(f"Summary report was sent successfully")
    else:
        tlogger.info(f"Summary text is empty or not enought long")

    summary_html = get_chat_summary_html(chat_summary, chat)
    tlogger.info(f"Send history pdf to chat (tg_id={telegram_id}) of '{avito_account.name}' ({location})")

    history_pdf.history_pdf_sender_task.delay(
    # history_pdf.history_pdf_sender_task(
        avito_account_id=avito_account.pk,
        chat=chat,
        summary_html=summary_html,
        telegram_id=telegram_id,
        trace_id=tlogger.trace_id,
    )

    last_chat_bot_task = all_tasks.last()
    if last_chat_bot_task is not None:
        last_chat_bot_task.summary_sanded = True
        last_chat_bot_task.save()


def get_chat_summary_text(chat_summary: ai_utils.ChatSummary, chat: messaging.api.Chat):
    counter = 1
    text = ("🎉 <b>Новый клиент из AVITO 🎉 \n\n</b> "
            "   📋 Сводка по переписке:\n\n")

    assert "context" in chat
    chat_context = chat["context"]["value"]

    title = chat_context.get("title") or "Без названия"
    text += f"🔹 {counter}. Название объявления: {title}\n"
    counter += 1

    client_name = chat.get("users", [])[0].get("name") or "Без имени"
    text += f"🔹 {counter}. Имя клиента: {client_name}\n"
    counter += 1

    #INFO ниже может быть без локации например через личку
    location = chat_context.get("location", {}).get("title") or "Без локации"
    text += f"🔸 {counter}. <u><b>Город обращения: {location}</b></u> \n"
    counter += 1

    paragraphs = {}

    if chat_summary.paragraphs:
        paragraphs = chat_summary.paragraphs.model_dump()

    for _, value in paragraphs.items():
        text += f"🔹 {counter}. {value} \n"
        counter += 1

    return text


def get_chat_summary_html(chat_summary: ai_utils.ChatSummary, chat: messaging.api.Chat):
    counter = 1
    text = "<div style='font-family: Arial, sans-serif;'><b>Сводка по переписке:</b><br><br>"

    assert "context" in chat
    chat_context = chat["context"]["value"]

    title = chat_context.get("title")

    if title and len(title) == 0:
        title = "Без названия"

    if title:
        text += f"<p style='margin-left: 20px;'>{counter}. Название объявления: {title}</p>"
        counter += 1

    location = chat_context.get("location")

    if location:
        city_name_from_item = location.get("title")
    else:
        city_name_from_item = "Без локации"

    if city_name_from_item:
        text += f"<p style='margin-left: 20px;'><b>{counter}. <u>Город обращения: {city_name_from_item}</u></b></p>"
        counter += 1

    paragraphs = {}

    if chat_summary.paragraphs:
        paragraphs = chat_summary.paragraphs.model_dump()

    for _, value in paragraphs.items():
        text += f"<p style='margin-left: 20px;'>{counter}. {value}</p>"
        counter += 1

    text += "</div>"

    return text
