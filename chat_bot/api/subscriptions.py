from pprint import pprint
import httpx
from avito_account.models.models import AvitoAccount
from base.exceptions import HTTPException
from base.settings import ENVIRONMENT


async def subscribe_to_messages(avito_account: AvitoAccount):
    await avito_account.update_refresh_token_async()
    url = "https://api.avito.ru/messenger/v3/webhook"
    headers = {'authorization': f"Bearer {avito_account.access_token}"}

    if ENVIRONMENT == "PRODUCTION":
        subscribe_url = "https://avitostata.ru/chat_bot/webhook_inbox"
    else:
        subscribe_url = "https://b181-2a0c-16c1-1-1500-225-c0ff-fe00-ef.ngrok-free.app/chat_bot/webhook_inbox"

    async with httpx.AsyncClient() as client:
        params = {"url": subscribe_url}
        response = await client.post(url, headers=headers, json=params)
        if response.status_code == 200:
            data = response.json()
            print(data)
            print("subscribe_to_messages called")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


async def stop_subscribe_to_messages(avito_account: AvitoAccount):
    await avito_account.update_refresh_token_async()
    url = "https://api.avito.ru/messenger/v1/webhook/unsubscribe"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    if ENVIRONMENT == "PRODUCTION":
        stop_subscribe_url = "https://avitostata.ru/chat_bot/webhook_inbox"
    else:
        stop_subscribe_url = "https://a163-31-128-32-122.ngrok-free.app/chat_bot/webhook_inbox"

    async with httpx.AsyncClient() as client:
        params = {"url": stop_subscribe_url}

        response = await client.post(url, headers=headers, json=params)
        if response.status_code == 200:
            data = response.json()
            print("stopped subscription")
            pprint(data)
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


async def check_subscriptions(avito_account: AvitoAccount):
    await avito_account.update_refresh_token_async()
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
