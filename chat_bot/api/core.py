import httpx
from avito_account.models.models import AvitoAccount


async def send_message_to_avito(avito_account: AvitoAccount, user_id: int, chat_id: str, message: str):
    url = f"https://api.avito.ru/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages"
    headers = {
        "Authorization": f"Bearer {avito_account.access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "message": {
            "text": message,
        },
        "type": "text"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


async def read_chat(avito_account: AvitoAccount, user_id: int, chat_id: str):
    url = f"https://api.avito.ru/messenger/v1/accounts/{user_id}/chats/{chat_id}/read"
    headers = {
        "Authorization": f"Bearer {avito_account.access_token}",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        response.raise_for_status()
        return response.json()
