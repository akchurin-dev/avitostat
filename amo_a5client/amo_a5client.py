from celery import shared_task

import amo_a5client.models
from amo_a5client.config import ORIGIN_NAME, RETRIES_DELAY_SEC
from amo_a5client.utils import amo_avito_links
from amo_a5client.utils import message_handling
from utils.logging import TraceLogger


def handle_message_from_amo(
    amo_account_id: int,
    contact_id: int,
    message_created_at_timestamp: int,
    text: str,
    *,
    tlogger: TraceLogger,
) -> None:

    amo_avito_links.remember_amo_message(
        amo_account_id=amo_account_id,
        contact_id=contact_id,
        message_created_at_ts=message_created_at_timestamp,
        text=text,
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
    retries: int = 3,
    *,
    trace_id: str,
) -> None:

    tlogger = TraceLogger(trace_id)
    tlogger.info({
        "AvitoA5Client message handling started": {
            "text": text,
        },
    })

    contact = amo_avito_links.get_amo_contact_by_avito_message(
        avito_account_id=avito_account_id,
        chat_id=chat_id,
        message_created_at_ts=message_created_at_timestamp,
        text=text,
        author_name="",
        tlogger=tlogger,
    )

    if contact is None:
        if retries == 0:
            tlogger.info("Stop handling. AmoContact not found")

        if retries > 0:
            tlogger.info(f"AmoContact not found. Retry found after {RETRIES_DELAY_SEC} sec")

            handle_message_from_avito.s(
                avito_account_id=avito_account_id,
                chat_id=chat_id,
                message_id=message_id,
                message_created_at_timestamp=message_created_at_timestamp,
                text=text,
                retries=retries - 1,
                trace_id=trace_id,
            ).apply_async(countdown=RETRIES_DELAY_SEC)

        return

    delay_sec = 60 * 3

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
