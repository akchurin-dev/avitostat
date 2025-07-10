from celery import shared_task

import amo_a5client.models
from amo_a5client import config
from amo_a5client.utils import message_handling
from utils.logging import TraceLogger


def handle_message_from_amo(
    amo_account_id: int,
    contact_id: int,
    lead_id: int | None,
    message_created_at_timestamp: int,
    text: str,
    attachment_type: str | None,
    *,
    tlogger: TraceLogger,
) -> None:

    text_with_attachment = _include_attachment_to_text(text, attachment_type)
    link = amo_a5client.models.MessageContactLink.get_or_create_by_amo_data(
        message_created_at_ts=message_created_at_timestamp,
        text=text_with_attachment,
        author_name="",
        amo_account_id=amo_account_id,
        amo_contact_id=contact_id,
    )

    if link.avito_account_id and link.avito_chat_id and link.avito_message_id:
        _launch_message_handling(
            amo_account_id=amo_account_id,
            avito_account_id=link.avito_account_id,
            contact_id=contact_id,
            lead_id=lead_id,
            chat_id=link.avito_chat_id,
            message_id=link.avito_message_id,
            message_created_at_ts=link.message_created_at,
            text=text,
            tlogger=tlogger,
        )
    else:
        tlogger.info("Message not found")


@shared_task
def handle_message_from_avito(
    avito_account_id: int,
    amo_account_id: int,
    chat_id: str,
    message_id: str,
    message_created_at_timestamp: int,
    text: str,
    message_type: str,
    *,
    retry: bool =False,
    trace_id: str,
) -> None:

    tlogger = TraceLogger(trace_id)
    tlogger.info({
        "Handle avito message as a5client": {
            "text": text,
            "created_at_ts": message_created_at_timestamp,
        },
    })

    amo_attachment_type = {
        "image": "picture",
        "voice": "voice",
    }.get(message_type)

    text_with_attachment = _include_attachment_to_text(text, amo_attachment_type)

    link = amo_a5client.models.MessageContactLink.get_or_create_by_avito_data(
        message_created_at_ts=message_created_at_timestamp,
        text=text_with_attachment,
        author_name="",
        amo_account_id=amo_account_id,
        avito_account_id=avito_account_id,
        avito_chat_id=chat_id,
        avito_message_id=message_id,
    )

    if link.contact_id:
        _launch_message_handling(
            amo_account_id=amo_account_id,
            avito_account_id=avito_account_id,
            contact_id=link.contact_id,
            lead_id=None,
            chat_id=chat_id,
            message_id=message_id,
            message_created_at_ts=message_created_at_timestamp,
            text=text,
            tlogger=tlogger,
        )
    else:
        if not retry:
            handle_message_from_avito.s(
                avito_account_id=avito_account_id,
                amo_account_id=amo_account_id,
                chat_id=chat_id,
                message_id=message_id,
                message_created_at_timestamp=message_created_at_timestamp,
                text=text,
                message_type=message_type,
                retry=True,
                trace_id=tlogger.trace_id,
            ).apply_async(countdown=10)

        tlogger.info("Message not found")


def get_amo_avito_accounts_link(avito_account_id: int) -> amo_a5client.models.AmoAvitoAccountsLink | None:
    return (
        amo_a5client.models.AmoAvitoAccountsLink.objects
        .filter(avito_account_id=avito_account_id)
        .first()
    )


def _include_attachment_to_text(text: str, attachment_type: str | None) -> str:
    if attachment_type is None:
        return text

    if text:
        text += "\n\n---------------------\n\n"

    text += "Attachment type: " + attachment_type
    return text


def _launch_message_handling(
    amo_account_id: int,
    avito_account_id: int,
    contact_id: int,
    lead_id: int | None,
    chat_id: str,
    message_id: str,
    message_created_at_ts: int,
    text: str,
    *,
    tlogger: TraceLogger,
) -> None:

    delay_sec = 0
    tlogger.info(f"Wait {delay_sec} sec")

    message_handling.launch_new_message_handling.s(
        amo_account_id=amo_account_id,
        avito_account_id=avito_account_id,
        contact_id=contact_id,
        lead_id=lead_id,
        chat_id=chat_id,
        message_id=message_id,
        message_created_at_ts=message_created_at_ts,
        text=text,
        trace_id=tlogger.trace_id,
    ).apply_async(countdown=delay_sec)
