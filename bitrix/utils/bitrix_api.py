from typing import assert_never
from typing import Literal

import httpx
from loguru import logger

from django.conf import settings

from bitrix.utils import accounts as bitrix_accounts


async def get(bitrix_domain: str, operation: str, params=None) -> httpx.Response:
    return await request(
        bitrix_domain=bitrix_domain,
        operation=operation,
        method="GET",
        params=params,
    )


async def post(bitrix_domain: str, operation: str, json=None) -> httpx.Response:
    return await request(
        bitrix_domain=bitrix_domain,
        operation=operation,
        method="POST",
        json=json,
    )


async def request(
    *,
    bitrix_domain: str,
    operation: str,
    method: Literal["GET", "POST"],
    params=None,
    json=None,
    retry=False
) -> httpx.Response:

    account = await bitrix_accounts.get_bitrix_account(bitrix_domain, raise_not_exist_exception=True)
    if account:
        access_token = account.access_token

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    url = f"https://{bitrix_domain}/rest/{operation}"

    async with httpx.AsyncClient() as client:
        if method == "GET":
            response = await client.get(url, params=params, headers=headers)
        elif method == "POST":
            response = await client.post(url, json=json, headers=headers)
        else:
            assert_never(method)

    if not retry and _is_expired_token(response):
        await refresh_token(bitrix_domain)
        return await request(
            bitrix_domain=bitrix_domain,
            operation=operation,
            method=method,
            params=params,
            json=json,
            retry=True,
        )

    if not response.is_success:
        logger.info(f"Not success response from bitrix status={response.status_code} data={response.json()}")

    return response


async def refresh_token(bitrix_domain: str):
    """ https://apidocs.bitrix24.ru/api-reference/oauth/auto-renewal.html """

    url = "https://oauth.bitrix.info/oauth/token/"

    account = await bitrix_accounts.get_bitrix_account(bitrix_domain, raise_not_exist_exception=True)
    if account:
        refresh_token = account.refresh_token

    params = {
        "grant_type": "refresh_token",
        "client_id": settings.BITRIX_OAUTH_CLIENT_ID,
        "client_secret": settings.BITRIX_OAUTH_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()

    data = response.json()

    access_token = data["access_token"]
    refresh_token = data["refresh_token"]

    await bitrix_accounts.update_tokens(bitrix_domain, access_token, refresh_token)

    logger.info(f"New token {access_token}")


def _is_expired_token(response: httpx.Response) -> bool:
    if response.status_code != 401:
        return False

    error = response.json().get("error")
    return error == "expired_token"
