import httpx
from avito_account.models.models import AvitoAccount


async def get_balance(avito_account: AvitoAccount):
    await avito_account.update_refresh_token_async()
    url = f"https://api.avito.ru/core/v1/accounts/{avito_account.id}/balance/"
    headers = {
        "Authorization": f"Bearer {avito_account.access_token}",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        if response.status_code == 200:
            balance = response.json().get("real")
            return balance
