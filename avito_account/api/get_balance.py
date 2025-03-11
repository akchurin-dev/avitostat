from avito_account import avito_api
from avito_account.models.models import AvitoAccount


async def get_balance(avito_account: AvitoAccount):
    # await avito_account.update_refresh_token_async()
    action = f"/core/v1/accounts/{avito_account.pk}/balance/"
    headers = {
        "Authorization": f"Bearer {avito_account.access_token}",
    }

    response = avito_api.client.get(action, headers=headers)
    response.raise_for_status()
    if response.status_code == 200:
        balance = response.json().get("real")
        return balance
