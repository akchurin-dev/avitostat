from datetime import datetime, timedelta
import requests

from avito_account.api.api import get_items_list
from avito_account.models import AvitoAccount
from avito_account.oauth_utils import refresh_token
from conversion.utils import dates_for_period
from exceptions import HTTPException


def get_statistics_for_period(avito_account: AvitoAccount, period: str):
    # TODO проверить на аккаунте Абу Закарии пишет 429 -ту мани реквестс (может слишком много объявлений?)
    date_from, date_to = dates_for_period(period=period)
    items = get_items_list(avito_account)
    item_ids = [item.get('id') for item in items]

    url = f"https://api.avito.ru/stats/v1/accounts/{avito_account.id}/items"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}",
        'content-type': 'application/json',
    }

    params = {
        'dateFrom': date_from,
        'dateTo': date_to,
        'itemIds': item_ids,
        'periodGrouping': period
    }

    response = requests.post(url, headers=headers, json=params)
    if response.status_code == 200:
        statistic_for_all_items = response.json().get("result").get("items")
        statistics_correct = [item for item in statistic_for_all_items if len(item["stats"]) > 0]
        return statistics_correct
    elif response.status_code == 403 and response.json().get("result").get("message") == "access token expired":
        refresh_token(avito_account)
        # TODO переделать в миксины и убрать отсюда, добавить в остальные реквесты
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)
