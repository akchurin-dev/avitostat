import pprint
import re
from typing import Any

from asgiref.sync import async_to_sync
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_GET

from loguru import logger

from bitrix import tasks as bitrix_tasks
from bitrix.utils import accounts as bitrix_accounts
from bitrix.utils import ai_chat_bots as bitrix_ai_chat_bots
from bitrix.utils import bitrix_bots
from bitrix.utils import openlines as bitrix_openlines
from bitrix.utils import bitrix_installation


@login_required
@require_GET
def get_installation_link(request: HttpRequest, *args, **kwargs) -> HttpResponse:
    bitrix_domain = request.GET.get("bitrix_domain", None)
    user_id: int = request.user.id

    if bitrix_domain is None:
        return HttpResponseBadRequest("bitrix_domain is required")
    
    bitrix_installation.link_user_with_bitrix_domain(user_id, bitrix_domain)

    return JsonResponse({
        "link": bitrix_installation.get_installation_link(bitrix_domain),
    })


@csrf_exempt
@require_http_methods(["HEAD", "POST"])
def bitrix_app_installed(request: HttpRequest, *args, **kwargs) -> HttpResponse:
    if request.method == "HEAD":
        return HttpResponse(status=200)
    
    bitrix_domain, err1 = _get_request_value(request.POST.dict(), "auth[domain]")
    access_token, err2 = _get_request_value(request.POST.dict(), "auth[access_token]")
    refresh_token, err3 = _get_request_value(request.POST.dict(), "auth[refresh_token]")

    err = err1 or err2 or err3
    if err:
        logger.warning(err)
        return HttpResponseBadRequest()

    owner_id = bitrix_installation.get_user_id(bitrix_domain)
    
    if owner_id is None:
        logger.info(f"Bitrix domain '{bitrix_domain}' not associated with user")
        return HttpResponse(status=204)

    async_to_sync(bitrix_accounts.create_bitrix_account)(bitrix_domain, owner_id, access_token, refresh_token)
    logger.info(f"new access {access_token}")
    async_to_sync(bitrix_bots.register_bitrix_chat_bot)(bitrix_domain)
    async_to_sync(bitrix_openlines.activate_bot)(bitrix_domain)

    return HttpResponse(status=204)


@csrf_exempt
@require_http_methods(["HEAD", "POST"])
def bitrix_bot_event(request: HttpRequest, *args, **kwargs) -> HttpResponse:
    if request.POST.get("event", "") != "ONIMBOTMESSAGEADD":
        return HttpResponse(status=204)

    chat_id, err1 = _get_request_value(request.POST.dict(), "data[PARAMS][CHAT_ID]")
    dialog_id, err2 = _get_request_value(request.POST.dict(), "data[PARAMS][DIALOG_ID]")
    bitrix_domain, err3 = _get_request_value(request.POST.dict(), r"data\[BOT\]\[\d+\]\[AUTH\]\[domain\]", regex=True)

    err = err1 or err2 or err3
    if err:
        logger.warning(err)
        return HttpResponseBadRequest()

    chat_bot = async_to_sync(bitrix_ai_chat_bots.define_chat_bot)(bitrix_domain, dialog_id)

    if chat_bot is None:
        async_to_sync(bitrix_openlines.redirect_client_to_manager)(bitrix_domain, chat_id)
        logger.info(f"Chat bot for bitrix dialog (dialog_id={dialog_id}) not found. Dialog redirected to manager.")
        return HttpResponse(status=204)

    bitrix_tasks.generate_answer.delay(bitrix_domain, dialog_id, chat_bot.id)

    return HttpResponse(status=204)


def _get_request_value(data: dict, key: str, regex: bool = False, required: bool = True) -> tuple[Any, str | None]:
    if regex:
        keys = [k for k in data.keys() if re.match(key, k)]

        if len(keys) == 0:
            data_str = pprint.pformat(data)
            return "", f"Pattern {key} not found in request data. Got\n{data_str}"

        return data.get(keys[0], ""), None

    value = data.get(key, "")
    err = None

    if required and value is None:
        data_str = pprint.pformat(data)
        err = f"{key} not found in request data. Got\n{data_str}"

    return value, err
