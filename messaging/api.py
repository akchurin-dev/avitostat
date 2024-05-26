import httpx
from avito_account.models import AvitoAccount
from exceptions import HTTPException


# TODO ДОБАВИТЬ ПРОВЕРКУ НА ПРОСРОЧЕННОСТЬ и обновление токена
async def get_chats(avito_account: AvitoAccount, has_more: bool = True) -> dict:
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

    while has_more == True:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                has_more = response.json().get("meta").get("has_more")
                params["offset"] += 100
                chats.extend(response.json().get("chats"))
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
