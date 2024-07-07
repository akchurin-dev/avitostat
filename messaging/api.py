from avito_account.models import AvitoAccount
from exceptions import HTTPException
import httpx


# TODO ДОБАВИТЬ ПРОВЕРКУ НА ПРОСРОЧЕННОСТЬ и обновление токена
# статистика по последним 100 чатам не отличается если даже все чаты вытаскивать имей ввиду, возможно
# можно убрать цикл уайл и просто один запрос отправлять если будут сложности или будет медленно
async def get_chats(avito_account: AvitoAccount) -> dict:
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

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(url, headers=headers, params=params, timeout=180)
            if response.status_code == 200:
                data = response.json()
                chats.extend(data.get("chats", []))
                has_more = data.get("meta", {}).get("has_more", False)
                if not has_more:
                    break
                params["offset"] += 100
            elif response.status_code == 403:  # REMOVE THIS AND ADD DECORATOR
                await avito_account.update_refresh_token_async()
                print(response.status_code, response.text)
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
