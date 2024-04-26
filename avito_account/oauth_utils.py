import os
from typing import Any

import requests
from django.http import JsonResponse
from dotenv import load_dotenv

from avito_account.models import AvitoAccount
from exceptions import HTTPException

load_dotenv()
client_id = os.getenv('AVITO_CLIENT_ID')
client_secret = os.getenv('AVITO_CLIENT_SECRET')


def get_avito_tokens(code: str) -> JsonResponse | Any:
    url = 'https://api.avito.ru/token/'
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code
    }

    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)


def get_avito_account_info(access_token: str):
    url = 'https://api.avito.ru/core/v1/accounts/self'
    headers = {
        'authorization': f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)


def create_or_update_avito_account(code: str):
    # try:
    token_data = get_avito_tokens(code)
    access_token = token_data.get('access_token')
    account_info = get_avito_account_info(access_token)

    avito_id = int(account_info.get("id"))
    avito_account, created = AvitoAccount.objects.get_or_create(id=avito_id)

    avito_account.access_token = token_data.get('access_token')
    avito_account.refresh_token = token_data.get('refresh_token')
    avito_account.name = account_info.get('name')
    avito_account.phone = account_info.get('phone')
    avito_account.profile_url = account_info.get('profile_url')
    avito_account.save()

    # except HTTPException as e:
    #     return Response(e.detail, status=e.status_code)


def refresh_token(avito_account_id: int):
    avito_account = AvitoAccount.objects.get(id=avito_account_id)

    url = 'https://api.avito.ru/token/'
    data = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': avito_account.refresh_token
    }

    response = requests.post(url, data=data)
    response_data = response.json()

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    else:
        avito_account.access_token = response_data['access_token']
        avito_account.refresh_token = response_data['refresh_token']
        avito_account.save()
        return True
