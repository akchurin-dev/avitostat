from asgiref.sync import async_to_sync
from telegram_bot import bot

import amo.models
from amo.utils import amo_api
from amo.utils import amo_messages
from chat_bot import ai_utils
from utils.logging import TraceLogger


def send_report(
    account: amo.models.AmoAccount,
    lead_id: int | str,
    contact_id: int | str,
    messages: list[amo_messages.Message],
    *,
    tlogger: TraceLogger,
) -> None:

    messages_legacy_format = amo_messages.to_legacy_format(messages)
    ai_report = ai_utils.chat_summary_generator_typed(messages_legacy_format)

    lead = amo_api.get_lead(
        domain=account.domain,
        lead_id=lead_id,
        tlogger=tlogger,
    )

    contact = amo_api.get_contact(
        domain=account.domain,
        contact_id=contact_id,
        tlogger=tlogger,
    )

    summary_text = _get_summary_text(ai_report, lead, contact)

    if account.telegram_id is None:
        raise Exception("AmoAccount don't have telegram_id")

    async def f(chat_id: str, text: str):
        await bot.bot.session.close()
        await bot.bot.send_message(
            chat_id=chat_id,
            text=text,
        )

    async_to_sync(f)(account.telegram_id, summary_text)


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
        ]

    if paragraphs:
        for p in paragraphs:
            if p:
                summary_lines.append(f"{len(summary_lines)}. {p}")

    return "\n".join(summary_lines)
