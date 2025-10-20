from typing import NamedTuple

import amo.models
from base import settings
from utils import httpx_helper
from utils.logging import TraceLogger


class Tokens(NamedTuple):
    access_token: str
    refresh_token: str


def get_tokens(domain: str, code: str, *, tlogger: TraceLogger) -> Tokens:
    """ https://www.amocrm.ru/developers/content/oauth/step-by-step """

    url = "https://" + domain + "/oauth2/access_token"

    data = {
        "client_id": settings.AMO_INTEGRATION_ID,
        "client_secret": settings.AMO_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.AMO_REDIRECT_URI,
    }

    response = httpx_helper.request("POST", url, json=data, tlogger=tlogger)
    response.raise_for_status()

    json = response.json()

    return Tokens(
        access_token=json["access_token"],
        refresh_token=json["refresh_token"],
    )


def update_openapi_tokens(domain: str, refresh_token: str | None = None) -> None:
    """ https://www.amocrm.ru/developers/content/oauth/step-by-step#Получение-нового-access-token-по-его-истечении """

    url = f"https://{domain}/oauth2/access_token"

    if refresh_token is None:
        refresh_token = amo.models.AmoAccount.objects.get(domain=domain).refresh_token

    data = {
        "client_id": settings.AMO_INTEGRATION_ID,
        "client_secret": settings.AMO_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "redirect_uri": settings.AMO_REDIRECT_URI,
    }

    response = httpx_helper.request("POST", url, json=data)
    response.raise_for_status()

    response_data = response.json()

    amo.models.AmoAccount.objects.filter(domain=domain).update(
        access_token=response_data["access_token"],
        refresh_token=response_data["refresh_token"],
    )


def update_hidden_api_tokens(account_id: str | int, *, tlogger: TraceLogger) -> None:
    account = amo.models.AmoAccount.objects.get(amo_id=account_id)

    tokens = _get_hidden_api_tokens(
        domain=account.domain,
        refresh_token=account.cookies_refresh_token or "",
        login=account.amo_login,
        password=account.amo_password,
        tlogger=tlogger,
    )
    amojo_token = _get_amojo_token(
        domain=account.domain,
        refresh_token=tokens.refresh_token,
        access_token=tokens.access_token,
        csrf_token=tokens.csrf_token,
        session_id=tokens.session_id,
        tlogger=tlogger,
    )

    amo.models.AmoAccount.objects.filter(amo_id=account_id).update(
        amojo_access_token=amojo_token,
        cookies_session_id=tokens.session_id,
        cookies_csrf_token=tokens.csrf_token,
        cookies_access_token=tokens.access_token,
        cookies_refresh_token=tokens.refresh_token,
    )

    tlogger.info("Amo hidden api tokens was successfully updated")


class HiddenAPITokens(NamedTuple):
    access_token: str
    refresh_token: str
    csrf_token: str
    session_id: str


def _get_hidden_api_tokens(domain: str, refresh_token: str, login: str, password: str, *, tlogger: TraceLogger) -> HiddenAPITokens:
    response = _get_hidden_api_tokens_by_refresh(domain, refresh_token, tlogger=tlogger)

    if response.is_success:
        tlogger.info("Amo hidden api tokens refreshing is success")
        return _extract_hidden_api_tokens_from_cookies(dict(response.cookies))

    response = _login_to_amo(
        domain=domain,
        session_id=response.cookies["session_id"],
        csrf_token=response.cookies["csrf_token"],
        login=login,
        password=password,
        tlogger=tlogger,
    )

    if response.is_success:
        tlogger.info("Logining to amo is success")
        return _extract_hidden_api_tokens_from_cookies(dict(response.cookies))

    tlogger.error("Can't update hidden api tokens")
    raise Exception("Can't update hidden api tokens")


def _get_hidden_api_tokens_by_refresh(domain: str, refresh_token: str, *, tlogger: TraceLogger):
    tlogger.info("Start amo hidden api tokens refreshing")

    url = "https://" + domain + "/dashboard"

    headers = {
        "Cookie": "refresh_token=" + refresh_token,
    }

    response = httpx_helper.request("GET", url, headers=headers, tlogger=tlogger)

    if response.status_code != 401:
        response.raise_for_status()

    return response


def _login_to_amo(
    domain: str,
    session_id: str,
    csrf_token: str,
    login: str,
    password: str,
    *,
    tlogger: TraceLogger,
):
    tlogger.info("Start amo logining")

    url = "https://" + domain + "/oauth2/authorize"

    headers = {
        "Cookie": (
            "session_id=" + session_id + "; "
            "csrf_token=" + csrf_token + "; "
            "last_login=" + login
        ),
    }

    data = {
        "csrf_token": csrf_token,
        "password": password,
        "temporary_auth": "N",
        "username": login,
    }

    response = httpx_helper.request("POST", url, data=data, headers=headers, tlogger=tlogger)

    if response.status_code != 401:
        response.raise_for_status()

    return response


def _get_amojo_token(domain: str, refresh_token: str, access_token: str, csrf_token: str, session_id: str, *, tlogger: TraceLogger) -> str:
    url = "https://" + domain + "/ajax/v1/chats/session"

    data = {
        "request[chats][session][action]": "create",
    }

    headers = {
        "Cookie": (
            "refresh_token=" + refresh_token + "; "
            "access_token=" + access_token + "; "
            "csrf_token=" + csrf_token + "; "
            "session_id=" + session_id
        ),
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 YaBrowser/25.2.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }

    response = httpx_helper.request("POST", url, data=data, headers=headers, tlogger=tlogger)
    response.raise_for_status()

    return response.json()["response"]["chats"]["session"]["access_token"]


def _extract_hidden_api_tokens_from_cookies(cookies: dict) -> HiddenAPITokens:
    return HiddenAPITokens(
        access_token=cookies["access_token"],
        refresh_token=cookies["refresh_token"],
        csrf_token=cookies["csrf_token"],
        session_id=cookies["session_id"],
    )
