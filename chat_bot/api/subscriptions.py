from pprint import pprint
import httpx
from avito_account.models.models import AvitoAccount
from base.exceptions import HTTPException
from base import settings
from utils.logging import TraceLogger


def subscribe_for_messages(account: AvitoAccount, *, raise_error: bool, tlogger: TraceLogger) -> None:
    url = "https://api.avito.ru/messenger/v3/webhook"

    headers = {'authorization': f"Bearer {account.access_token}"}

    params = {"url": f"https://{settings.AVITO_WEBHOOK_HOST}/chat_bot/webhook_inbox"}

    with httpx.Client() as client:
        response = client.post(url, headers=headers, json=params)

    if raise_error:
        response.raise_for_status()

    data = response.json()

    tlogger.info(data)
    tlogger.info(f"'{account.name}' subscribed for messages successfully")


def unsubscribe_from_messages(account: AvitoAccount, *, raise_error: bool, tlogger: TraceLogger) -> None:
    url = "https://api.avito.ru/messenger/v1/webhook/unsubscribe"

    headers = {
        'authorization': f"Bearer {account.access_token}"
    }

    params = {"url": f"https://{settings.AVITO_WEBHOOK_HOST}/chat_bot/webhook_inbox"}

    with httpx.Client() as client:
        response = client.post(url, headers=headers, json=params)

    if raise_error:
        response.raise_for_status()

    data = response.json()

    tlogger.info(f"'{account.name}' stopped subscription successfully")
    tlogger.info(data)


async def asubscribe_to_messages(avito_account: AvitoAccount):
    await avito_account.update_refresh_token_async()
    url = "https://api.avito.ru/messenger/v3/webhook"
    headers = {'authorization': f"Bearer {avito_account.access_token}"}

    subscribe_url = f"https://{settings.AVITO_WEBHOOK_HOST}/chat_bot/webhook_inbox"

    async with httpx.AsyncClient() as client:
        params = {"url": subscribe_url}
        response = await client.post(url, headers=headers, json=params)
        if response.status_code == 200:
            data = response.json()
            print(data)
            print("subscribe_to_messages called")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


async def astop_subscribe_to_messages(avito_account: AvitoAccount):
    # await avito_account.update_refresh_token_async()
    url = "https://api.avito.ru/messenger/v1/webhook/unsubscribe"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    stop_subscribe_url = f"https://{settings.AVITO_WEBHOOK_HOST}/chat_bot/webhook_inbox"

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
    # await avito_account.update_refresh_token_async()
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
