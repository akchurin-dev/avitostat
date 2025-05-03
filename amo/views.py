import datetime

from django.http import HttpResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

import amo.models
import amo.serializers
import amo.schemas
import amo.tasks
from amo.utils import amo_ai
from amo.utils import amo_accounts
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
    tlogger = logging.TraceLogger()

    if not isinstance(request.data, dict):
        raise Exception()

    tlogger.info(dict(request.data))

    try:
        account_id: int = int(request.data["account[id]"])
        contact_id = int(request.data["message[add][0][contact_id]"])
        origin = request.data["message[add][0][origin]"]
        chat_id: str = request.data["message[add][0][chat_id]"]
        talk_id: int = int(request.data["message[add][0][talk_id]"])
        message_id: str = request.data["message[add][0][id]"]
        text: str = request.data["message[add][0][text]"]
        message_created_at: datetime.datetime = datetime.datetime.fromtimestamp(
            timestamp=int(request.data["message[add][0][created_at]"]),
            tz=datetime.timezone.utc,
        )

        entity_type: str | None = request.data.get("message[add][0][entity_type]")
        lead_id: int | None = None
        if entity_type == "lead":
            lead_id = int(request.data["message[add][0][entity_id]"])

        attachment_type: str | None = request.data.get("message[add][0][attachment][type]")
        file_link: str | None = None
        if attachment_type:
            file_link = request.data.get("message[add][0][attachment][link]")
    except:
        tlogger.info("Error when parse request data, request data =")
        tlogger.info(dict(request.data))
        raise

    amo.tasks.launch_chatbottask(
        account_id=account_id,
        contact_id=contact_id,
        lead_id=lead_id,
        origin=origin,
        chat_id=chat_id,
        talk_id=talk_id,
        message_id=message_id,
        message_created_at=message_created_at,
        text=text,
        file_type=attachment_type,
        file_link=file_link,
        trace_id=tlogger.trace_id,
    )

    return Response(status=status.HTTP_200_OK)


@api_view(["PATCH"])
def syncronize_amo_account(request: Request, pk: int) -> Response:
    tlogger = logging.TraceLogger()

    account = amo.models.AmoAccount.objects.get(pk=pk)

    amo_pipelines.syncronize_pipelines(account.domain, tlogger=tlogger)
    amo_sources.scan_new_origins(account.amo_id, tlogger=tlogger)

    return Response(status=status.HTTP_200_OK)


@api_view(["PATCH"])
def update_prompt_example(request: Request, pk: int) -> Response:
    chatbot = amo.models.AmoChatBot.objects.get(pk=pk)
    prompt = amo_ai.get_example_prompt(chatbot)
    amo.models.AmoChatBot.objects.filter(pk=pk).update(prompt_example=prompt)

    return Response(status=status.HTTP_200_OK)
