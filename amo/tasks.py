from celery import shared_task

from amo.utils import message_handling
from amo.utils import notes_handling
from amo.utils import amo_webhooks
from utils.logging import TraceLogger


@shared_task
def handle_amo_webhook(request_data: dict):
    tlogger = TraceLogger()

    webhook_type = amo_webhooks.get_webhook_type(request_data)

    tlogger.info({
        "webhook_type": webhook_type and webhook_type.name,
        "request_data": request_data,
    })

    if webhook_type is None:
        tlogger.info("Stop handling. Unknown webhook type")
        return

    if webhook_type == amo_webhooks.WebhookType.NEW_INCOMING_MESSAGE:
        message_handling.handle_new_message_webhook(request_data, tlogger=tlogger)

    if webhook_type == amo_webhooks.WebhookType.NEW_NOTE_LEAD:
        notes_handling.handle_new_lead_note_webhook(request_data, tlogger=tlogger)
