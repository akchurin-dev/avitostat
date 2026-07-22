from django.db import transaction
from django.db.models import QuerySet

import messaging.api
from avito_account.models.models import AvitoAccount
from chat_bot import ai_utils
from chat_bot.models import ChatBotTask
from chat_bot.utils import contacts_detection
from chat_bot.utils import history_pdf
from chat_bot.utils import summaries
from utils import tg
from utils.logging import TraceLogger


@transaction.atomic
def send_summary(account: AvitoAccount, chat_id, *, trace_id: str | None = None):
    tlogger = TraceLogger(trace_id)

    locked_tasks = list(
        ChatBotTask.objects
        .filter(avito_account=account, chat_id=chat_id)
        .select_for_update(no_key=True)
        .order_by("created_at")
    )

    if summaries.any_contact_report_sent(locked_tasks):
        tlogger.info(f"Stop summary sending. Summary report already sent for chat_id {chat_id}.")
        return

    messages = messaging.api.get_chat_last_50_messages_by_chat_id(account, chat_id, tlogger=tlogger).get("messages")

    if not messages:
        tlogger.info("Stop summary sending. No messages in chat")
        return

    chat = messaging.api.get_chat_by_id(account, chat_id, tlogger=tlogger)
    chat["messages"] = messages

    if not contacts_detection.chat_has_contact(account, chat_id, messages):
        tlogger.info(f"Stop summary sending. No phone/contact in chat tasks or messages for chat_id {chat_id}")
        return

    chat_summary = ai_utils.generate_chat_summary("Avito", account.name or "", messages)

    ChatBotTask.objects.filter(avito_account=account, chat_id=chat_id).update(summary_sanded=True)

    summary_sender(account, chat_summary, chat, locked_tasks, tlogger=tlogger)


def summary_sender(
    avito_account: AvitoAccount,
    chat_summary: ai_utils.ChatSummary,
    chat: messaging.api.Chat,
    all_tasks: QuerySet[ChatBotTask] | list[ChatBotTask],
    *,
    tlogger: TraceLogger,
):
    summary_text = get_chat_summary_text(chat_summary, chat)
    tlogger.info(f"Summary report summary_text {summary_text}.")

    telegram_id = avito_account.telegram_id
    location = "Location not defined"

    tasks_qs = all_tasks
    if isinstance(all_tasks, list):
        task_with_company_branch = next(
            (task for task in reversed(all_tasks) if task.company_branch_id),
            None,
        )
    else:
        task_with_company_branch = tasks_qs.filter(company_branch__isnull=False).order_by("created_at").last()
    if task_with_company_branch:
        assert task_with_company_branch.company_branch
        telegram_id = task_with_company_branch.company_branch.telegram_id
        location = task_with_company_branch.company_branch.location

    if telegram_id is None:
        error = "telegram_id is None"
        tlogger.error(error)
        raise Exception(error)

    if summary_text and len(summary_text) > 20:
        tlogger.info(f"Send summary report to chat (tg_id={telegram_id}) of '{avito_account.name}' ({location})")
        tg.send_message(telegram_id, summary_text)
        tlogger.info("Summary report was sent successfully")
    else:
        tlogger.info("Summary text is empty or not enought long")

    summary_html = get_chat_summary_html(chat_summary, chat)
    tlogger.info(f"Send history pdf to chat (tg_id={telegram_id}) of '{avito_account.name}' ({location})")

    history_pdf.history_pdf_sender_task.delay(
        avito_account_id=avito_account.pk,
        chat=chat,
        summary_html=summary_html,
        telegram_id=telegram_id,
        trace_id=tlogger.trace_id,
    )


def _summary_paragraph_items(chat_summary: ai_utils.ChatSummary) -> list[tuple[str, str]]:
    if not chat_summary.paragraphs:
        return []

    return [
        (key, value)
        for key, value in chat_summary.paragraphs.model_dump().items()
        if value and not key.startswith("meta__")
    ]


def get_chat_summary_text(chat_summary: ai_utils.ChatSummary, chat: messaging.api.Chat):
    assert "context" in chat
    chat_context = chat["context"]["value"]

    title = chat_context.get("title") or "Без названия"
    client_name = chat.get("users", [])[0].get("name") or "Без имени"
    location = chat_context.get("location", {}).get("title") or "Без локации"

    parts = [
        "🎉 <b>Новый клиент из AVITO 🎉</b>",
        "",
        "   📋 Сводка по переписке:",
        "",
        f"🔹 1. Название объявления: {title}",
        f"🔹 2. Имя клиента: {client_name}",
        f"🔸 3. <u><b>Город обращения: {location}</b></u>",
    ]

    counter = 4
    for _, value in _summary_paragraph_items(chat_summary):
        parts.append(f"🔹 {counter}. {value}")
        counter += 1

    return "\n".join(parts)


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

    for _, value in _summary_paragraph_items(chat_summary):
        text += f"<p style='margin-left: 20px;'>{counter}. {value}</p>"
        counter += 1

    text += "</div>"

    return text
