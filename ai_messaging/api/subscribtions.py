from pprint import pprint

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
            "url": "https://eb85-31-128-32-122.ngrok-free.app/ai_messaging/webhook_inbox",
        }

        response = await client.post(url, headers=headers, json=params)
        if response.status_code == 200:
            data = response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


async def stop_subscribe_to_messages(avito_account: AvitoAccount):
    url = "https://api.avito.ru/messenger/v1/webhook/unsubscribe"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    async with httpx.AsyncClient() as client:
        params = {
            "url": "https://9d19-31-128-32-122.ngrok-free.app/ai_messaging/webhook_inbox",
        }

        response = await client.post(url, headers=headers, json=params)
        if response.status_code == 200:
            data = response.json()
            pprint(data)
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


async def check_subscriptions(avito_account: AvitoAccount):
    url = "https://api.avito.ru/messenger/v1/subscriptions"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, )
        print("its RESPONSE")
        pprint(response.json())
        print(response.status_code)
        if response.status_code == 200:
            data = response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
