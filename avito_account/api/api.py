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



