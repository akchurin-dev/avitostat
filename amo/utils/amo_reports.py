from asgiref.sync import async_to_sync
from telegram_bot import bot

import amo.models
from amo.utils import amo_api
from amo.utils import amo_messages
from chat_bot import ai_utils
from utils import tg
from utils.logging import TraceLogger


def send_report(
    account: amo.models.AmoAccount,
    lead: amo_api.Lead,
    contact: amo_api.Contact,
    messages: list[amo_messages.Message],
    *,
    tlogger: TraceLogger,
) -> None:

    messages_legacy_format = amo_messages.to_legacy_format(messages)
    ai_report = ai_utils.generate_chat_summary("Amo", account.domain, messages_legacy_format)

    summary_text = _get_summary_text(ai_report, lead, contact)

    if account.telegram_id is None:
        raise Exception("AmoAccount don't have telegram_id")

    tg.send_message(account.telegram_id, summary_text)


def _get_summary_text(ai_report: ai_utils.ChatSummary, lead: amo_api.Lead, contact: amo_api.Contact) -> str:
    summary_lines = ["Новый клиент"]

    if lead.custom_fields_values:
        for field_value in lead.custom_fields_values:
            summary_lines.append(f"{len(summary_lines)}. {field_value.field_name} - {field_value.values[0].value}")

    if contact.custom_fields_values:
        for field_value in contact.custom_fields_values:
            summary_lines.append(f"{len(summary_lines)}. {field_value.field_name} - {field_value.values[0].value}")

    paragraphs = None
    if ai_report.paragraphs:
        paragraphs = [
            ai_report.paragraphs.paragraph1,
            ai_report.paragraphs.paragraph2,
            ai_report.paragraphs.paragraph3,
            ai_report.paragraphs.paragraph4,
        ]

    if paragraphs:
        for p in paragraphs:
            if p:
                summary_lines.append(f"{len(summary_lines)}. {p}")

    return "\n".join(summary_lines)
