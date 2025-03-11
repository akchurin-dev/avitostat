import time
from typing import Literal

import httpx
from loguru import logger

from tests.utils import avitostat_test_api
from utils import httpx_helper


avito_client = httpx_helper.create_client(
    base_url="https://api.avito.ru",
    timeout=httpx.Timeout(30, read=5),
    retries=3,
)


def get(avito_account_id: int, action: str, params: dict | None = None):
    return request(
        avito_account_id=avito_account_id,
        action=action,
        method="GET",
        params=params,
    )


def post(avito_account_id: int, action: str, data: dict | None = None, json = None, params: dict | None = None):
    return request(
        avito_account_id=avito_account_id,
        action=action,
        method="POST",
        data=data,
        json=json,
        params=params,
    )


def request(
    avito_account_id: int,
    action: str,
    method: Literal["GET", "POST"],
    data: dict | None = None,
    json = None,
    params: dict | None = None,
    retry: bool = False
):
    avito_account = avitostat_test_api.get_avito_account(avito_account_id)
    if avito_account.access_token is None:
        raise Exception(f"AvitoAccount ({avito_account_id}) dont have access-token")

    headers = {
        "Authorization": "Bearer " + avito_account.access_token
    }

    if method == "GET":
        response = avito_client.get(action, headers=headers, params=params)

    if method == "POST":
        response = avito_client.post(action, data=data, json=json, params=params, headers=headers)

    time.sleep(0.5)

    if not retry and _is_token_expired(response):
        refresh_token(avito_account_id)
        return request(
            avito_account_id=avito_account_id,
            action=action,
            method=method,
            data=data,
            json=json,
            retry=True,
        )

    if not response.is_success:
        logger.warning((
            f"Request to avito {action} is not success. "
            f"Got status={response.status_code}, content={response.text}"
        ))

    return response


def _is_token_expired(response: httpx.Response) -> bool:
    if response.status_code != 403:
        return False

    message = response.json().get("result", {}).get("message")
    
    return message == "access token expired"


def refresh_token(avito_account_id: int):
    raise NotImplementedError()
