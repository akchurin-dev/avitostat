import httpx
from avito_account.models.models import AvitoAccount
from base.exceptions import HTTPException


async def subscribe_to_messages(avito_account: AvitoAccount):
    url = "https://api.avito.ru/messenger/v3/webhook"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    async with httpx.AsyncClient() as client:
        params = {
            "url": "https://eb91-31-128-32-122.ngrok-free.app/ai_messaging/webhook_inbox/",
            # "url": "https://yandex.ru",
        }

        response = await client.post(url, headers=headers, json=params)
        print("its RESPONSE")
        print(response.json())
        print(response.status_code)
        if response.status_code == 200:
            data = response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


async def check_subscriptions(avito_account: AvitoAccount):
    url = "https://api.avito.ru/messenger/v1/subscriptions"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    async with httpx.AsyncClient() as client:
        params = {
            "subscriptions": [
                {
                    "url": "https://eb91-31-128-32-122.ngrok-free.app/ai_messaging/webhook_inbox",
                    "version": "3"
                }
            ]
        }

        response = await client.post(url, headers=headers, json=params)
        print("its RESPONSE")
        print(response.json())
        print(response.status_code)
        if response.status_code == 200:
            data = response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
