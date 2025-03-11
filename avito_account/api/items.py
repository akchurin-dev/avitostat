from avito_account import avito_api
from avito_account.models.models import AvitoAccount
from base.exceptions import HTTPException


class ItemsApiSync:

    @staticmethod
    def get_item_info(avito_account: AvitoAccount, item_id: str) -> dict:
        action = f"/core/v1/accounts/{avito_account.pk}/items/{item_id}/"
        headers = {
            'authorization': f"Bearer {avito_account.access_token}"
        }

        response = avito_api.client.get(action, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())


async def get_items_list(avito_account: AvitoAccount):
    action = f"/core/v1/items"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    params = {
        'per_page': 100,
        'status': 'active',
        'page': 1
    }

    response = avito_api.client.get(action, headers=headers, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    all_items = []
    while response.status_code == 200 and response.json().get('resources'):
        all_items += response.json().get('resources')
        params['page'] += 1
        response = avito_api.client.get(action, headers=headers, params=params)

    if len(all_items) == 0:
        raise HTTPException(status_code=404, detail="Avito account does not have active items in period")
    else:
        return all_items
