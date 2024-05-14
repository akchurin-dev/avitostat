from avito_account.api.api import get_items_list
from avito_account.models import AvitoAccount
from avito_account.oauth_utils import refresh_token
from conversion.utils import dates_for_period_without_extra_reserve
from exceptions import HTTPException
import requests
from typing import Any


def get_statistics_for_period(avito_account: AvitoAccount, period: str) -> tuple[list[Any], list[dict] | None]:
    date_from, date_to = dates_for_period_without_extra_reserve(period=period)
    date_from = date_from.strftime("%Y-%m-%d")
    date_to = date_to.strftime("%Y-%m-%d")

    items = get_items_list(avito_account)
    item_ids = [item.get('id') for item in items]

    url = f"https://api.avito.ru/stats/v1/accounts/{avito_account.id}/items"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}",
        'content-type': 'application/json',
    }

    # Splitting item_ids into chunks of 200 or less
    item_chunks = [item_ids[i:i + 200] for i in range(0, len(item_ids), 200)]

    all_statistics = []

    for chunk in item_chunks:
        params = {
            'dateFrom': date_from,
            'dateTo': date_to,
            'itemIds': chunk,
            'periodGrouping': period
        }

        response = requests.post(url, headers=headers, json=params)

        if response.status_code == 200:
            statistic_for_all_items = response.json().get("result").get("items")
            statistics_correct = [item for item in statistic_for_all_items if len(item["stats"]) > 0]
            all_statistics.extend(statistics_correct)
        elif response.status_code == 403 and response.json().get("result").get("message") == "access token expired":
            refresh_token(avito_account)
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    return all_statistics, items
