from pprint import pprint

from django.conf import settings

from avito_account import avito_api
from avito_account.models.models import AvitoAccount
from base.exceptions import HTTPException
from base.settings import ENVIRONMENT


async def subscribe_to_messages(avito_account: AvitoAccount):
    await avito_account.update_refresh_token_async()
    action = "https://api.avito.ru/messenger/v3/webhook"
    headers = {'authorization': f"Bearer {avito_account.access_token}"}

    if ENVIRONMENT == "PRODUCTION":
        subscribe_url = "https://avitostata.ru/chat_bot/webhook_inbox"
    else:
        subscribe_url = f"https://{settings.AVITO_WEBHOOK_HOST}/chat_bot/webhook_inbox"

    params = {"url": subscribe_url}
    response = avito_api.client.post(action, headers=headers, json=params)
    if response.status_code == 200:
        data = response.json()
        print(data)
        print("subscribe_to_messages called")
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)


async def stop_subscribe_to_messages(avito_account: AvitoAccount):
    # await avito_account.update_refresh_token_async()
    action = "/messenger/v1/webhook/unsubscribe"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    if ENVIRONMENT == "PRODUCTION":
        stop_subscribe_url = "https://avitostata.ru/chat_bot/webhook_inbox"
    else:
        stop_subscribe_url = f"https://{settings.AVITO_WEBHOOK_HOST}/chat_bot/webhook_inbox"

    params = {"url": stop_subscribe_url}

    response = avito_api.client.post(action, headers=headers, json=params)
    if response.status_code == 200:
        data = response.json()
        print("stopped subscription")
        pprint(data)
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)


async def check_subscriptions(avito_account: AvitoAccount):
    # await avito_account.update_refresh_token_async()
    action = "/messenger/v1/subscriptions"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    response = avito_api.client.post(action, headers=headers, )
    print("its RESPONSE")
    pprint(response.json())
    print(response.status_code)
    if response.status_code == 200:
        data = response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)
