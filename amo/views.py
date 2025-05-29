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
from amo.utils import amo_accounts
from amo.utils import amo_pipelines
from amo.utils import amo_sources
from amo.utils import amo_webhooks
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


@api_view(["GET"])
def application_disabled_callback(request: Request) -> Response:
    return Response(status=status.HTTP_200_OK)


@api_view(["POST"])
def amo_webhook(request: Request) -> Response:
    if isinstance(request.data, dict):
        amo.tasks.handle_amo_webhook.delay(request.data)

    return Response(status=status.HTTP_200_OK)


@api_view(["PATCH"])
def syncronize_amo_account(request: Request, pk: int) -> Response:
    tlogger = logging.TraceLogger()

    account = amo.models.AmoAccount.objects.get(pk=pk)

    amo_pipelines.syncronize_pipelines(account, tlogger=tlogger)
    amo_sources.scan_new_origins(account.amo_id, tlogger=tlogger)

    return Response(status=status.HTTP_200_OK)
