from pprint import pprint
import requests
from avito_account.models import AvitoAccount


def get_items_list(avito_account: AvitoAccount) -> list[dict] | None:
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


import requests
from pprint import pprint


def statistic(avito_account: AvitoAccount):
    url = f"https://api.avito.ru/stats/v1/accounts/{avito_account.id}/items"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}",
        'content-type': 'application/json',
    }
    params = {
        'dateFrom': "2024-01-01",
        'dateTo': "2024-04-01",
        # 'fields': 'uniqViews, uniqContacts, uniqFavorites',
        'itemIds': [3456191202, 3359934271],
        'periodGrouping': "month"
    }

    response = requests.post(url, headers=headers, json=params)
    return response.json()


def main():
    avito_account = AvitoAccount.objects.get(id=359794245).lost()
    info = statistic(avito_account=avito_account)
    pprint(info)


if __name__ == "__main__":
    main()
