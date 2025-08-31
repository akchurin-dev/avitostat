from datetime import timedelta

from avito_account.api.items import get_items_list
from avito_account.models.models import AvitoAccount
from avito_account.models.models import ExcludedItem
from conversion.utils import iso_dates_for_period_without_extra_reserve
from base.exceptions import HTTPException
import httpx


async def items_excluded_filter(avito_account: AvitoAccount, items: list):
    filtered_items = []
    excluded_ids = [item.id async for item in ExcludedItem.objects.filter(avito_account=avito_account)]
    for item in items:
        if item.get("id") not in excluded_ids:
            filtered_items.append(item)
    return filtered_items


async def get_statistics_for_period(avito_account: AvitoAccount, period: str):
    iso_date_from, iso_date_to = iso_dates_for_period_without_extra_reserve(period=period)

    items = await get_items_list(avito_account)
    if type(items) is not list:
        raise HTTPException(status_code=404, detail="Avito account not have active items in period")

    if type(items) is list:
        items = await items_excluded_filter(avito_account, items)

    item_ids = [item.get('id') for item in items]

    url = f"https://api.avito.ru/stats/v1/accounts/{avito_account.pk}/items"
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
                'dateFrom': iso_date_from,
                'dateTo': iso_date_to,
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

    return all_statistics, items, iso_date_from, iso_date_to
