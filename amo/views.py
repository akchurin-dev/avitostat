import datetime

from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

import amo.serializers
import amo.schemas
from amo.utils import amo_accounts
from amo.utils import message_handling
from amo.utils import amo_pipelines
from amo.utils import amo_sources
from base import settings
from utils import logging


@api_view(["GET"])
def oauth_callback(request: Request) -> HttpResponse:
    tlogger = logging.TraceLogger()

    serializer = amo.serializers.OauthCallbackQueryParamsSerializer(data=request.query_params.dict())
    serializer.is_valid(raise_exception=True)
    if isinstance(serializer.validated_data, dict):
        data = serializer.validated_data

    client_id = data["client_id"]
    if client_id != settings.AMO_INTEGRATION_ID:
        tlogger.info(f"Request contains other integration id, got '{client_id}'")
        return Response(
            status=status.HTTP_400_BAD_REQUEST,
            data={"message": f"Unknown client_id='{client_id}'"},
        )

    state = amo.schemas.OauthStateSchema.model_validate_json(data["state"])
    domain = data["referer"]

    account = amo_accounts.create_account_or_update_tokens(
        domain=domain,
        code=data["code"],
        created_by_id=state.created_by_id,
        tlogger=tlogger,
    )

    amo_pipelines.syncronize_pipelines(domain, tlogger=tlogger)

    try:
        amo_sources.scan_new_origins(account.amo_id, tlogger=tlogger)
        tlogger.info("Origins scan is success")
    except:
        tlogger.info("Origins scan isn't success")

    return redirect(f"/admin/amo/amoaccount/{account.amo_id}/change/")


@api_view(["POST"])
def webhook_inbox(request: Request) -> Response:
    if not isinstance(request.data, dict):
        raise Exception()

    account_id: int = int(request.data["account[id]"])
    entity_type = request.data["message[add][0][entity_type]"]
    lead_id: int | None = int(request.data["message[add][0][entity_id]"]) if entity_type == "lead" else None
    contact_id = request.data["message[add][0][contact_id]"]
    origin = request.data["message[add][0][origin]"]
    chat_id: str = request.data["message[add][0][chat_id]"]
    talk_id: int = int(request.data["message[add][0][talk_id]"])
    message_id: str = request.data["message[add][0][id]"]
    message_created_at: datetime.datetime = datetime.datetime.fromtimestamp(
        timestamp=int(request.data["message[add][0][created_at]"]),
        tz=datetime.UTC,
    )
    text: str = request.data["message[add][0][text]"]

    message_handling.launch_handler(
        account_id=account_id,
        lead_id=lead_id,
        contact_id=contact_id,
        origin=origin,
        chat_id=chat_id,
        talk_id=talk_id,
        message_id=message_id,
        message_created_at=message_created_at,
        text=text,
        trace_id=logging.new_trace_id(),
    )

    return Response(status=status.HTTP_200_OK)
