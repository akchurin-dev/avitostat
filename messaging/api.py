import datetime
import json

from django.conf import settings
from httpx import HTTPStatusError
from loguru import logger

from avito_account import avito_api
from avito_account.models.models import AvitoAccount
from base.exceptions import HTTPException
from conversion.utils import dates_for_period_without_extra_reserve


# TODO ДОБАВИТЬ ПРОВЕРКУ НА ПРОСРОЧЕННОСТЬ и обновление токена
# статистика по последним 100 чатам не отличается если даже все чаты вытаскивать имей ввиду, возможно
# можно убрать цикл уайл и просто один запрос отправлять если будут сложности или будет медленно

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


async def get_chats(avito_account: AvitoAccount, period: str = "week", max_retries: int = 3) -> list:
    action = f"/messenger/v2/accounts/{avito_account.pk}/chats"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    params = {
        "unread_only": False,
        "limit": 50,
        "offset": 0,
    }
    chats = []
    retries = 0

    while params.get("offset") < 1000:
        response = avito_api.client.get(action, headers=headers, params=params, timeout=180)
        if response.status_code == 200:
            data = response.json()
            chats.extend(data.get("chats", []))
            has_more = data.get("meta", {}).get("has_more", False)
            last_chat_in_period = await timestamp_in_period(timestamp=chats[-1].get("updated"), period=period)
            if not has_more or not last_chat_in_period:
                break
            params["offset"] += 50
        elif response.status_code == 403:
            retries += 1
            if retries > max_retries:
                raise HTTPStatusError("Превышено максимальное количество попыток обновления токена",
                                        request=response.request, response=response)
            print(
                f"Attempt {retries}: {response.status_code}, {response.text}")  # Удалить если нет необходимости в коде, была нужда когда разбирался в ошибкой 403 бесконечно
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

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


async def get_chats_last_50_messages(avito_account: AvitoAccount, chats: list) -> list:
    if len(chats) > 0:
        for chat in chats:
            chat_id = chat.get("id")
            action = f"/messenger/v3/accounts/{avito_account.pk}/chats/{chat_id}/messages/"
            headers = {'authorization': f"Bearer {avito_account.access_token}"}
            params = {"limit": 50, "offset": 0}
            response = avito_api.client.get(action, headers=headers, params=params, timeout=300)
            if response.status_code == 200:
                new_messages = response.json().get("messages")
                if len(new_messages) == 0:
                    break
                new_messages = _filter_messages(new_messages[::-1])
                _print_chat(new_messages)
                chat["messages"] = new_messages
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
    return chats


class MessagingAPISync:
    @staticmethod
    def get_chats_last_50_messages(avito_account: AvitoAccount, chats: list) -> list:
        if len(chats) > 0:
            for chat in chats:
                chat_id = chat.get("id")
                action = f"/messenger/v3/accounts/{avito_account.pk}/chats/{chat_id}/messages/"
                headers = {'authorization': f"Bearer {avito_account.access_token}"}
                params = {"limit": 50, "offset": 0}
                response = avito_api.client.get(action, headers=headers, params=params, timeout=300)
                if response.status_code == 200:
                    new_messages = response.json().get("messages")
                    if len(new_messages) == 0:
                        break
                    new_messages = _filter_messages(new_messages[::-1])
                    _print_chat(new_messages)
                    chat["messages"] = new_messages
                else:
                    raise HTTPException(status_code=response.status_code, detail=response.text)
        return chats

    @staticmethod
    def get_chat_by_id(avito_account: AvitoAccount, chat_id: str):
        action = f"/messenger/v2/accounts/{avito_account.pk}/chats/{chat_id}"
        headers = {
            'authorization': f"Bearer {avito_account.access_token}"
        }
        params = {
            "unread_only": False,
            "limit": 1,
            "offset": 0,
        }
        response = avito_api.client.get(action, headers=headers, params=params)

        if response.status_code == 200:
            chat = response.json()
            return chat
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


    @staticmethod
    def get_chat_last_50_messages_by_chat_id(avito_account: AvitoAccount, chat_id: str):
        action = f"/messenger/v3/accounts/{avito_account.pk}/chats/{chat_id}/messages/"
        headers = {'authorization': f"Bearer {avito_account.access_token}"}
        params = {"limit": 50, "offset": 0}
        response = avito_api.client.get(action, headers=headers, params=params)
        if response.status_code == 200:
            messages = response.json().get("messages")[::-1]
            messages = _filter_messages(messages)
            _print_chat(messages)
            return messages
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


async def get_calls_statistic_last_week(avito_account: AvitoAccount):
    # await avito_account.update_refresh_token_async()
    date_from, date_to = await dates_for_period_without_extra_reserve(period="week", date_type="str")

    action = f"/core/v1/accounts/{avito_account.pk}/calls/stats/"
    headers = {'authorization': f"Bearer {avito_account.access_token}",
                "Content-Type": "application/json", }
    params = {"dateFrom": f"{date_from}", "dateTo": f"{date_to}"}

    response = avito_api.client.post(action, headers=headers, json=params)
    if response.status_code == 200:
        data = json.loads(response.text)
        if data['result']:
            return data
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)


def _filter_messages(messages: list) -> list:
    import httpx

    if settings.ENVIRONMENT != "TESTING":
        return messages

    url = f"{settings.TEST_DJANGO_HOST}/deep_tests/prev-session-last-avito-message"

    response = httpx.get(url)
    response.raise_for_status()

    prev_session_last_message_id = response.text
    result = []

    for msg in messages[::-1]:
        if msg["id"] == prev_session_last_message_id:
            break

        result.append(msg)

    return result[::-1]


def _print_chat(messages: list):
    lines: list[str] = ["Read messages"]
    
    for msg in messages:
        direction = msg["direction"]
        text = msg.get("content", {}).get("text")
        lines.append(f"{direction}: {text}")

    logger.info("\n".join(lines))
