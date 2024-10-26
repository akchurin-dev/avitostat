from datetime import timedelta
from asgiref.sync import sync_to_async
from avito_account.api.api import get_items_list
from avito_account.models.excluded_items import ExcludedItem
from avito_account.models.models import AvitoAccount
from conversion.utils import dates_for_period_without_extra_reserve
from base.exceptions import HTTPException
import httpx


async def items_excluded_filter(avito_account: AvitoAccount, items: list):
    filtered_items = []
    excluded_items = await sync_to_async(list)(ExcludedItem.objects.filter(avito_account_id=avito_account.id))
    excluded_ids = [item.id for item in excluded_items]
    for item in items:
        if item.get("id") not in excluded_ids:
            filtered_items.append(item)
    return filtered_items


async def get_statistics_for_period(avito_account: AvitoAccount, period: str):
    date_from, date_to = await dates_for_period_without_extra_reserve(period=period, date_type="str")

    items = await get_items_list(avito_account)
    if type(items) is not list:
        raise HTTPException(status_code=404, detail="Avito account not have active items in period")

    if type(items) is list:
        items = await items_excluded_filter(avito_account, items)

    item_ids = [item.get('id') for item in items]

    url = f"https://api.avito.ru/stats/v1/accounts/{avito_account.id}/items"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}",
        'content-type': 'application/json',
    }

    # Splitting item_ids into chunks of 200 or less
    item_chunks = [item_ids[i:i + 200] for i in range(0, len(item_ids), 200)]

    all_statistics = []

    async with httpx.AsyncClient() as client:
        for chunk in item_chunks:
            params = {
                'dateFrom': date_from,
                'dateTo': date_to,
                'itemIds': chunk,
                'periodGrouping': period
            }

            response = await client.post(url, headers=headers, json=params, timeout=300)

            if response.status_code == 200:
                data = response.json()
                statistic_for_all_items = data.get("result").get("items")
                statistics_correct = [item for item in statistic_for_all_items if len(item["stats"]) > 0]
                all_statistics.extend(statistics_correct)
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)

    return all_statistics, items, date_from, date_to
