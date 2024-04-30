from pprint import pprint
import requests
from avito_account.models import AvitoAccount


def get_items_list(avito_account: AvitoAccount) -> list[dict] | None:
    # TODO Добавить функционал если в БД нет таких айтемов чтобы сразу добавились
    url = f"https://api.avito.ru/core/v1/items"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    params = {
        'per_page': 100,
        'status': 'active, removed, old, blocked, rejected',
        'page': 1
        # 'updatedAtFrom':
        # 'category':
    }
    response = requests.get(url, headers=headers, params=params)

    all_pages = []
    while response.status_code == 200 and response.json().get('resources'):
        all_pages += response.json().get('resources')
        params['page'] += 1
        response = requests.get(url, headers=headers, params=params)
    return all_pages


def get_item_info(access_token: str, user_id: str, item_id: str) -> dict:
    url = f"https://api.avito.ru/core/v1/accounts/{user_id}/items/{item_id}/"
    headers = {
        'authorization': f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    return response.json()


def get_statistics(avito_account: AvitoAccount):
    url = f"https://api.avito.ru/stats/v1/accounts/{avito_account.id}/items"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}",
        'content-type': 'application/json',
    }

    items = get_items_list(avito_account)
    item_ids = [item.get('id') for item in items]
    params = {
        'dateFrom': "2021-01-01",
        'dateTo': "2021-08-01",
        # 'fields': 'uniqViews, uniqContacts, uniqFavorites',
        'itemIds': item_ids,
        'periodGrouping': "month"
    }

    response = requests.post(url, headers=headers, json=params)
    if response.status_code == 200:
        statistic_for_all_items = response.json().get("result").get("items")
        statistics_correct = [item for item in statistic_for_all_items if len(item["stats"]) > 0]
        return statistics_correct


