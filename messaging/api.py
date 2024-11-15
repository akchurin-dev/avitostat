import json
import pprint
from datetime import timedelta, datetime

from avito_account.models.models import AvitoAccount
from base.exceptions import HTTPException
import httpx
from httpx import HTTPStatusError

from base.settings import NOW_IN_MOSCOW, moscow_tz
from conversion.utils import dates_for_period_without_extra_reserve


# статистика по последним 100 чатам не отличается если даже все чаты вытаскивать имей ввиду, возможно
# можно убрать цикл уайл и просто один запрос отправлять если будут сложности или будет медленно
async def get_chats(avito_account: AvitoAccount, max_retries: int = 3) -> list:
    url = f"https://api.avito.ru/messenger/v2/accounts/{avito_account.id}/chats"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    params = {
        "unread_only": False,
        "limit": 100,
        "offset": 0,
    }
    chats = []
    retries = 0

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(url, headers=headers, params=params, timeout=180)
            if response.status_code == 200:
                data = response.json()
                chats.extend(data.get("chats", []))
                has_more = data.get("meta", {}).get("has_more", False)

                dt = datetime.fromtimestamp(data.get("chats")[-1].get("created"), tz=moscow_tz)
                timedelta = NOW_IN_MOSCOW - dt

                if not has_more or timedelta.days > 35:
                    break
                params["offset"] += 100
            elif response.status_code == 403:
                retries += 1
                if retries > max_retries:
                    raise HTTPStatusError("Превышено максимальное количество попыток обновления токена",
                                          request=response.request, response=response)
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

    return chats


async def get_chats_messages(avito_account: AvitoAccount, chats: list) -> list:
    if len(chats) > 0:
        async with httpx.AsyncClient() as client:
            for chat in chats:
                chat_id = chat.get("id")
                url = f"https://api.avito.ru/messenger/v3/accounts/{avito_account.id}/chats/{chat_id}/messages/"
                headers = {'authorization': f"Bearer {avito_account.access_token}"}
                params = {"limit": 30}

                response = await client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    chat["messages"] = response.json().get("messages")[::-1]
                else:
                    continue
    return chats


async def get_calls_statistic_last_period(avito_account: AvitoAccount, period: "week"):
    date_from, date_to = await dates_for_period_without_extra_reserve(period=period, date_type="str")

    async with httpx.AsyncClient() as client:
        url = f"https://api.avito.ru/core/v1/accounts/{avito_account.id}/calls/stats/"
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
