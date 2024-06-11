from functools import wraps

import httpx
import requests
from django.http import JsonResponse

from avito_account.models import AvitoAccount
from exceptions import HTTPException


# def handle_403_and_retry(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         avito_account = args[0]  # Предполагаем, что avito_account передается первым аргументом
#         try:
#             return func(*args, **kwargs)
#         except HTTPException as e:
#             if e.status_code == 403:
#                 avito_account.update_refresh_token()
#                 return func(*args, **kwargs)
#             else:
#                 raise e
#         except requests.exceptions.HTTPError as e:
#             if e.response.status_code == 403:
#                 avito_account.update_refresh_token()
#                 return func(*args, **kwargs)
#             else:
#                 raise e
#
#     return wrapper


async def get_items_list(avito_account: AvitoAccount):
    url = f"https://api.avito.ru/core/v1/items"
    headers = {
        'authorization': f"Bearer {avito_account.access_token}"
    }

    params = {
        'per_page': 100,
        'status': 'active',
        'page': 1
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.json())

        all_items = []
        while response.status_code == 200 and response.json().get('resources'):
            all_items += response.json().get('resources')
            params['page'] += 1
            response = await client.get(url, headers=headers, params=params)

        if len(all_items) == 0:
            raise HTTPException(status_code=404, detail="Avito account does not have active items in period")
        else:
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
