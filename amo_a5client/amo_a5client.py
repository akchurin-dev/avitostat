from celery import shared_task

import amo_a5client.models
from amo_a5client import config
from amo_a5client.utils import amo_avito_links
from amo_a5client.utils import message_handling
from utils import increasing_delay
from utils.logging import TraceLogger


def handle_message_from_amo(
    amo_account_id: int,
    contact_id: int,
    message_created_at_timestamp: int,
    text: str,
    attachment_type: str | None,
    *,
    tlogger: TraceLogger,
) -> None:

    text_with_attachment = _include_attachment_to_text(text, attachment_type)
    amo_avito_links.remember_amo_message(
        amo_account_id=amo_account_id,
        contact_id=contact_id,
        message_created_at_ts=message_created_at_timestamp,
        text=text_with_attachment,
        author_name="",
        tlogger=tlogger,
    )


@shared_task
def handle_message_from_avito(
    avito_account_id: int,
    chat_id: str,
    message_id: str,
    message_created_at_timestamp: int,
    text: str,
    message_type: str,
    time_left_for_retries_sec: float = 0,
    *,
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

    contact = amo_avito_links.get_amo_contact_by_avito_message(
        avito_account_id=avito_account_id,
        chat_id=chat_id,
        message_created_at_ts=message_created_at_timestamp,
        text=text_with_attachment,
        author_name="",
        tlogger=tlogger,
    )

    if contact is None:
        timeout = increasing_delay.is_timeout(time_left_for_retries_sec, config.RETRIES_DELAY_CONFIG)

        if timeout:
            tlogger.info("Stop handling. AmoContact finding timed out")

        if not timeout:
            retry_delay_sec = increasing_delay.next_delay(time_left_for_retries_sec, config.RETRIES_DELAY_CONFIG).total_seconds()
            tlogger.info(f"AmoContact not found. Retry after {retry_delay_sec} sec")

            handle_message_from_avito.s(
                avito_account_id=avito_account_id,
                chat_id=chat_id,
                message_id=message_id,
                message_created_at_timestamp=message_created_at_timestamp,
                text=text,
                message_type=message_type,
                time_left_for_retries_sec=time_left_for_retries_sec + retry_delay_sec,
                trace_id=trace_id,
            ).apply_async(countdown=retry_delay_sec)

        return

    delay_sec = 0
    tlogger.info(f"Wait {delay_sec} sec")

    message_handling.launch_new_message_handling.s(
        amo_account_id=contact.amo_account.pk,
        avito_account_id=avito_account_id,
        contact_id=contact.contact_id,
        lead_id=None,
        chat_id=chat_id,
        message_id=message_id,
        message_created_at_ts=message_created_at_timestamp,
        text=text,
        trace_id=tlogger.trace_id,
    ).apply_async(countdown=delay_sec)


def avito_account_handleble(avito_account_id: int) -> bool:
    return (
        amo_a5client.models.AmoAvitoAccountsLink.objects
        .filter(avito_account_id=avito_account_id)
        .exists()
    )


def _include_attachment_to_text(text: str, attachment_type: str | None) -> str:
    if attachment_type is None:
        return text

    if text:
        text += "\n\n---------------------\n\n"

    text += "Attachment type: " + attachment_type
    return text
