from avito_account.models.models import AvitoAccount
from base.exceptions import HTTPException
from utils import httpx_helper
from utils.logging import TraceLogger


class ItemsApiSync:
    @staticmethod
    def get_item_info(avito_account: AvitoAccount, item_id: str) -> dict:
        url = f"https://api.avito.ru/core/v1/accounts/{avito_account.pk}/items/{item_id}/"

        response = httpx_helper.request(
            method="GET",
            url=url,
            headers=httpx_helper.add_bearer(None, avito_account.access_token or ""),
        )
        response.raise_for_status()

        return response.json()


async def get_items_list(avito_account: AvitoAccount):
    tlogger = TraceLogger()

    url = f"https://api.avito.ru/core/v1/items"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    page = 1
    all_items = []

    while True:
        params = {
            'per_page': 100,
            'status': 'active',
            'page': page,
        }

        response = httpx_helper.request("GET", url, headers=headers, params=params, tlogger=tlogger)

        if not response.is_success:
            break

        resources: list | None = response.json().get("resources")

        if resources is None or len(resources) == 0:
            break

        all_items.extend(resources)
        page += 1

    if len(all_items) == 0:
        raise HTTPException(status_code=404, detail="Avito account does not have active items in period")

    return all_items
