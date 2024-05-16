from functools import wraps
import requests
from avito_account.models import AvitoAccount
from exceptions import HTTPException


def handle_403_and_retry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        avito_account = args[0]  # Предполагаем, что avito_account передается первым аргументом
        try:
            return func(*args, **kwargs)
        except HTTPException as e:
            if e.status_code == 403:
                avito_account.update_refresh_token()
                return func(*args, **kwargs)
            else:
                raise e
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                avito_account.update_refresh_token()
                return func(*args, **kwargs)
            else:
                raise e
    return wrapper


@handle_403_and_retry
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

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())

    all_items = []
    while response.status_code == 200 and response.json().get('resources'):
        all_items += response.json().get('resources')
        params['page'] += 1
        response = requests.get(url, headers=headers, params=params)
    return all_items


def get_item_info(access_token: str, user_id: str, item_id: str) -> dict:
    url = f"https://api.avito.ru/core/v1/accounts/{user_id}/items/{item_id}/"
    headers = {
        'authorization': f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.json())
