from datetime import datetime, timedelta

import requests

from avito_account.api.api import get_items_list
from avito_account.models import AvitoAccount
from avito_account.oauth_utils import refresh_token
from exceptions import HTTPException


def get_statistics_for_period(avito_account: AvitoAccount, period: str):
    # Проверяем, что значение периода входит в список допустимых значений
    valid_periods = ['month', 'week', 'day']
    if period not in valid_periods:
        raise ValueError("Invalid period. Please choose from 'month', 'week', or 'day'.")

    items = get_items_list(avito_account)
    item_ids = [item.get('id') for item in items]

    # Определяем диапазон дат в зависимости от выбранного периода
    today = datetime.now()
    date_to = today.strftime("%Y-%m-%d")
    if period == 'month':
        date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    elif period == 'week':
        date_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    else:  # Период 'day'
        date_from = (today - timedelta(days=1)).strftime("%Y-%m-%d")

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

# OLD VERSION
# def get_statistics(avito_account: AvitoAccount, period: str):
#     # TODO  сделать чтобы принимал один из трёх возможных знгачений
#
#     url = f"https://api.avito.ru/stats/v1/accounts/{avito_account.id}/items"
#     headers = {
#         'authorization': f"Bearer {avito_account.access_token}",
#         'content-type': 'application/json',
#     }
#
#     items = get_items_list(avito_account)
#     item_ids = [item.get('id') for item in items]
#     params = {
#         'dateFrom': "2021-01-01",
#         'dateTo': "2021-08-01",
#         # 'fields': 'uniqViews, uniqContacts, uniqFavorites',
#         'itemIds': item_ids,
#         'periodGrouping': "week"
#     }
#
#     response = requests.post(url, headers=headers, json=params)
#     if response.status_code == 200:
#         statistic_for_all_items = response.json().get("result").get("items")
#         statistics_correct = [item for item in statistic_for_all_items if len(item["stats"]) > 0]
#         return statistics_correct
