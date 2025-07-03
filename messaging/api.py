import datetime
import json
from typing import Literal
from typing import TypedDict

import httpx
from httpx import HTTPStatusError
from loguru import logger

from avito_account.models.models import AvitoAccount
from base import settings
from base.exceptions import HTTPException
from conversion.utils import dates_for_period_without_extra_reserve
from utils import httpx_helper
from utils.logging import TraceLogger


MAX_MESSAGES_ON_DEBUG = 5


class ChatMessageContent(TypedDict, total=False):
    text: str | None
    voice: dict[Literal["voice_id"], str] | None
    image: dict[Literal["sizes"], dict[str, str]] | None


class ChatMessage(TypedDict):
    id: str
    author_id: int
    direction: Literal["in", "out"]
    type: Literal["text", "image", "link", "item", "location", "call", "deleted", "voice", "system"]
    content: ChatMessageContent


class ChatContextValue(TypedDict, total=False):
    id: int
    title: str
    location: dict[Literal["title"], str]


class ChatContext(TypedDict):
    value: ChatContextValue


class ChatUser(TypedDict):
    id: int
    name: str


class Chat(TypedDict, total=False):
    id: str
    created: int
    updated: int
    context: ChatContext
    messages: list[ChatMessage]
    users: list[ChatUser]


async def timestamp_in_period(timestamp: int, period: str = "week") -> bool:
    start = datetime.datetime.fromtimestamp(timestamp)
    end = datetime.datetime.now()
    delta = end - start
    if period == "day":
        if delta.days <= 1:
            return True
    if period == "week":
        if delta.days <= 7:
            return True
    if period == "month":
        if delta.days <= 31:
            return True
    return False


async def get_chats(avito_account: AvitoAccount, period: str = "week", max_retries: int = 3) -> list[Chat]:
    url = f"https://api.avito.ru/messenger/v2/accounts/{avito_account.pk}/chats"

    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    params = {
        "unread_only": False,
        "limit": 50,
        "offset": 0,
    }

    chats: list[Chat] = []
    retries = 0

    async with httpx.AsyncClient() as client:
        while params["offset"] < 1000:
            response = await client.get(url, headers=headers, params=params, timeout=180)

            if response.status_code == 403:
                retries += 1
                if retries > max_retries:
                    logger.error((
                        "Not success response in get_chats function. "
                        f"Got status=403, data={response.text}"
                    ))
                    raise HTTPStatusError("Превышено максимальное количество попыток обновления токена",
                                          request=response.request, response=response)
                print(f"Attempt {retries}: {response.status_code}, {response.text}")  # Удалить если нет необходимости в коде, была нужда когда разбирался в ошибкой 403 бесконечно

            response.raise_for_status()

            data: dict = response.json()
            chats.extend(data.get("chats", []))

            has_more = data.get("meta", {}).get("has_more", False)

            last_chat_timestamp = chats[-1].get("updated")
            assert last_chat_timestamp
            last_chat_in_period = await timestamp_in_period(last_chat_timestamp, period)

            if not has_more or not last_chat_in_period:
                break

            params["offset"] += 50

    return chats


async def check_timestamp_in_period(timestamp: int, period: str = "week") -> bool:
    timestamp_in_period = False
    now = datetime.datetime.now()

    created_or_updated = datetime.datetime.fromtimestamp(timestamp)
    timedelta = now - created_or_updated

    if period == "week":
        if 7 >= timedelta.days >= 0:
            timestamp_in_period = True
    if period == "month":
        if 30 >= timedelta.days >= 0:
            timestamp_in_period = True
    return timestamp_in_period


async def get_chats_last_50_messages(avito_account: AvitoAccount, chats: list[Chat], *, trace_id: str | None = None) -> list[Chat]:
    tlogger = TraceLogger(trace_id)

    async with httpx.AsyncClient() as client:
        for chat in chats:
            chat_id = chat.get("id")
            url = f"https://api.avito.ru/messenger/v3/accounts/{avito_account.pk}/chats/{chat_id}/messages/"
            headers = {'authorization': f"Bearer {avito_account.access_token}"}
            params = {"limit": 50, "offset": 0}
            response = await client.get(url, headers=headers, params=params, timeout=300)

            if not response.is_success:
                httpx_helper.log_about_not_success_response(response, tlogger)
                continue

            new_messages = response.json().get("messages")[::-1]
            if len(new_messages) == 0:
                continue

            new_messages = _filter_messages(new_messages)
            _print_chat(new_messages, tlogger=tlogger)

            chat["messages"] = new_messages

    return chats


import requests
class MessagingAPISync:
    @staticmethod
    def get_chats_last_50_messages(avito_account: AvitoAccount, chats: list[Chat], *, trace_id: str | None = None) -> list[Chat]:
        tlogger = TraceLogger(trace_id)

        with httpx.Client() as client:
            for chat in chats:
                chat_id = chat.get("id")
                url = f"https://api.avito.ru/messenger/v3/accounts/{avito_account.pk}/chats/{chat_id}/messages/"
                headers = {'authorization': f"Bearer {avito_account.access_token}"}
                params = {"limit": 50, "offset": 0}
                response = client.get(url, headers=headers, params=params, timeout=300)

                if not response.is_success:
                    httpx_helper.log_about_not_success_response(response, tlogger)
                    continue

                new_messages = response.json().get("messages")[::-1]
                if len(new_messages) == 0:
                    continue

                new_messages = _filter_messages(new_messages)
                _print_chat(new_messages, tlogger=tlogger)

                chat["messages"] = new_messages

        return chats

    @staticmethod
    def get_chat_by_id(avito_account: AvitoAccount, chat_id: str) -> Chat:
        url = f"https://api.avito.ru/messenger/v2/accounts/{avito_account.pk}/chats/{chat_id}"
        headers = {
            'authorization': f"Bearer {avito_account.access_token}"
        }
        params = {
            "unread_only": False,
            "limit": 1,
            "offset": 0,
        }

        response = requests.get(url, headers=headers, params=params, timeout=180)
        response.raise_for_status()

        return response.json()


    @staticmethod
    def get_chat_last_50_messages_by_chat_id(avito_account: AvitoAccount, chat_id: str, *, trace_id: str | None = None) -> Chat:
        tlogger = TraceLogger(trace_id)

        url = f"https://api.avito.ru/messenger/v3/accounts/{avito_account.pk}/chats/{chat_id}/messages/"

        headers = {'authorization': f"Bearer {avito_account.access_token}"}
        params = {"limit": 50, "offset": 0}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            tlogger.error(f"Error when get avito messages. Got status {response.status_code}. Error: {response.text[:300]}")
            raise HTTPException(status_code=response.status_code, detail=response.text)

        messages = response.json().get("messages")[::-1]
        messages = _filter_messages(messages)
        _print_chat(messages, tlogger=tlogger)

        return {
            "id": chat_id,
            "messages": messages,
        }


async def get_calls_statistic_last_week(avito_account: AvitoAccount):
    # await avito_account.update_refresh_token_async()
    date_from, date_to = await dates_for_period_without_extra_reserve(period="week", date_type="str")

    async with httpx.AsyncClient() as client:
        url = f"https://api.avito.ru/core/v1/accounts/{avito_account.pk}/calls/stats/"
        headers = {'authorization': f"Bearer {avito_account.access_token}",
                   "Content-Type": "application/json", }
        params = {"dateFrom": f"{date_from}", "dateTo": f"{date_to}"}

        response = await client.post(url, headers=headers, json=params)
        if response.status_code == 200:
            data = json.loads(response.text)
            if data['result']:
                return data
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


def get_voice_id_url_pairs(
    account: AvitoAccount,
    voices_ids: list[str],
    *,
    tlogger: TraceLogger,
) -> dict[str, str]:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/getVoiceFiles """

    action = f"/messenger/v1/accounts/{account.pk}/getVoiceFiles"
    params = {"voice_ids": voices_ids}

    response = avito_api_request(
        method="GET",
        action=action,
        account=account,
        params=params,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return response.json()["voices_urls"]


def avito_api_request(
    method: httpx_helper.MethodType,
    action: str,
    account: AvitoAccount,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | list | None = None,
    headers: dict | None = None,
    *,
    tlogger: TraceLogger,
):
    url = "https://api.avito.ru" + action

    assert account.access_token
    headers = httpx_helper.add_bearer(headers, account.access_token)

    return httpx_helper.request(
        method=method,
        url=url,
        params=params,
        data=data,
        json=json,
        headers=headers,
        tlogger=tlogger,
    )


def _filter_messages(messages: list) -> list:
    if settings.ENVIRONMENT == "DEVELOPMENT":
        return messages[-MAX_MESSAGES_ON_DEBUG:]

    if settings.ENVIRONMENT != "TESTING":
        return messages

    url = settings.DJANGO_BASE_URL + "/deep_tests/prev-session-last-avito-message"

    response = httpx.get(url)
    response.raise_for_status()

    prev_session_last_message_id = response.text
    result = []

    for msg in messages[::-1]:
        if msg["id"] == prev_session_last_message_id:
            break

        result.append(msg)

    return result[::-1]


def _print_chat(messages: list, *, tlogger: TraceLogger):
    lines: list[str] = ["Get messages:"]

    for msg in messages:
        direction = msg["direction"]
        id = msg["id"]
        text = msg.get("content", {}).get("text")
        lines.append(f"{direction} ({id}): {text}")

    tlogger.info("\n".join(lines))
