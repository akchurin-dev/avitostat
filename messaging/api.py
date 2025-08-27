import datetime
import json
from typing import Literal
# from typing import TypedDict

import httpx
from httpx import HTTPStatusError
from loguru import logger
from typing import NamedTuple
from typing_extensions import TypedDict

from avito_account.models.models import AvitoAccount
from base import settings
from conversion.utils import iso_dates_for_period_without_extra_reserve
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
    created: int


class ChatContextValueLocation(TypedDict):
    title: str


class ChatContextValue(TypedDict, total=False):
    id: int
    title: str
    location: ChatContextValueLocation


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


class ChatListPage(NamedTuple):
    chats: list[Chat]
    has_more: bool


def timestamp_in_period(timestamp: int, period: str = "week") -> bool:
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


def get_chats(account: AvitoAccount, period: str = "week"):
    limit = 50
    offset = 0

    while offset < 1000:
        current_page, has_more = get_chat_list_page(account, offset, limit, tlogger=TraceLogger())

        for chat in current_page:
            yield chat

        if not has_more:
            return

        if len(current_page) == 0:
            return

        last_chat_timestamp = current_page[-1].get("updated", -1)
        last_chat_in_period = timestamp_in_period(last_chat_timestamp, period)

        if not last_chat_in_period:
            return

        offset += 50


def get_chat_list_page(account: AvitoAccount, offset: int, limit: int = 50, *, tlogger: TraceLogger) -> ChatListPage:
    action = f"/messenger/v2/accounts/{account.pk}/chats"

    params = {
        "unread_only": False,
        "limit": limit,
        "offset": offset,
    }

    response = avito_api_request("GET", action, account, params=params, tlogger=tlogger)
    response.raise_for_status()

    response_data: dict = response.json()

    return ChatListPage(
        chats=response_data["chats"],
        has_more=response_data.get("meta", {}).get("has_more", False)
    )


def get_chats_last_50_messages(avito_account: AvitoAccount, chats: list[Chat], *, tlogger: TraceLogger) -> list[Chat]:
    for chat in chats:
        chat_id = chat.get("id", "")
        chat_with_messages = get_chat_last_50_messages_by_chat_id(avito_account, chat_id, tlogger=tlogger)
        chat["messages"] = chat_with_messages.get("messages", [])

    return chats


def get_chat_by_id(avito_account: AvitoAccount, chat_id: str, tlogger: TraceLogger) -> Chat:
    action = f"/messenger/v2/accounts/{avito_account.pk}/chats/{chat_id}"

    params = {
        "unread_only": False,
        "limit": 1,
        "offset": 0,
    }

    response = avito_api_request("GET", action, avito_account, params=params, tlogger=tlogger)
    response.raise_for_status()

    return response.json()


def get_chat_last_50_messages_by_chat_id(avito_account: AvitoAccount, chat_id: str, *, tlogger: TraceLogger) -> Chat:
    action = f"/messenger/v3/accounts/{avito_account.pk}/chats/{chat_id}/messages/"

    params = {"limit": 50, "offset": 0}

    response = avito_api_request(
        method="GET",
        action=action,
        account=avito_account,
        params=params,
        tlogger=tlogger,
    )
    response.raise_for_status()

    messages = response.json().get("messages")[::-1]
    messages = _filter_messages(messages)
    _print_chat(messages, tlogger=tlogger)

    return {
        "id": chat_id,
        "messages": messages,
    }


def get_calls_statistic_last_week(account: AvitoAccount, *, tlogger: TraceLogger):
    action = f"/core/v1/accounts/{account.pk}/calls/stats/"

    iso_date_from, iso_date_to = iso_dates_for_period_without_extra_reserve(period="week")
    data = {
        "dateFrom": f"{iso_date_from}",
        "dateTo": f"{iso_date_to}",
    }

    response = avito_api_request("POST", action, account, json=data, tlogger=tlogger)
    response.raise_for_status()

    return response.json()


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
    headers = httpx_helper.add_header(headers, "Content-Type", "application/json")

    response = httpx_helper.request(
        method=method,
        url=url,
        params=params,
        data=data,
        json=json,
        headers=headers,
        tlogger=tlogger,
    )

    # if token expired:
    #   update token
    #   retry request

    return response


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
