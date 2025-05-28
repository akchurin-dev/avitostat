from __future__ import annotations

from enum import Enum

import amo.models
from amo.utils import amo_api
from base import settings
from utils.logging import TraceLogger


WEBHOOK_URL = "https://" + settings.AMO_WEBHOOK_DOMAIN + "/amo/webhook"
ACTIONS_SUBSCRIBE_TO = ["add_message", "note_lead"]


class WebhookType(Enum):
    NEW_INCOMING_MESSAGE = 1
    NEW_NOTE_LEAD = 2


def subscribe_for_webhooks(account: amo.models.AmoAccount, *, tlogger: TraceLogger) -> None:
    """ https://www.amocrm.ru/developers/content/crm_platform/webhooks-api#webhook-subscribe """

    action = "/api/v4/webhooks"

    data = {
        "destination": WEBHOOK_URL,
        "settings": ACTIONS_SUBSCRIBE_TO,
    }

    response = amo_api.openapi_request_by_account(
        account=account,
        method="POST",
        action=action,
        json=data,
        tlogger=tlogger,
    )
    response.raise_for_status()

    tlogger.info(f"Add subsription for new messages for domain '{account.domain}'")


def unsubscribe_from_webhooks(account: amo.models.AmoAccount, *, tlogger: TraceLogger) -> None:
    """ https://www.amocrm.ru/developers/content/crm_platform/webhooks-api#webhooks-delete """

    action = "/api/v4/webhooks"

    data = {
        "destination": WEBHOOK_URL,
    }

    response = amo_api.openapi_request_by_account(
        account=account,
        method="DELETE",
        action=action,
        data=data,
        tlogger=tlogger,
    )
    response.raise_for_status()

    tlogger.info(f"Delete new messages subscription for domain '{account.domain}'")


def get_webhook_type(request_data: dict) -> WebhookType | None:
    if "message[add][0]" in request_data:
        return WebhookType.NEW_INCOMING_MESSAGE

    if "note[lead][0]" in request_data:
        return WebhookType.NEW_NOTE_LEAD

    return None
