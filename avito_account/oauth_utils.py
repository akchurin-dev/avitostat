from avito_account.models.models import AvitoAccount
from base import settings
from base.exceptions import HTTPException
from utils import httpx_helper

client_id = settings.AVITO_CLIENT_ID
client_secret = settings.AVITO_CLIENT_SECRET


def get_avito_tokens(code: str):  # Если использованный токен -должен быть ексепшн, просто обновить код надо
    #TODO добавить сроки просрочки и проверку вынести в отдельный миксин перед отправкой запросов
    url = 'https://api.avito.ru/token/'
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code
    }

    response = httpx_helper.request(
        method="POST",
        url=url,
        data=data,
    )
    response.raise_for_status()

    return response.json()


def get_avito_account_info(access_token: str):
    url = 'https://api.avito.ru/core/v1/accounts/self'

    response = httpx_helper.request(
        method="GET",
        url=url,
        headers=httpx_helper.add_bearer(None, access_token),
    )
    response.raise_for_status()

    return response.json()


def create_or_update_avito_account(code: str, created_by_id: int) -> AvitoAccount:
    token_data = get_avito_tokens(code)
    access_token = token_data.get('access_token')
    account_info = get_avito_account_info(access_token)

    avito_id = int(account_info.get("id"))
    avito_account, created = AvitoAccount.objects.update_or_create(
        id=avito_id,
        defaults={
            'created_by_id': created_by_id,
            'access_token': access_token,
            'refresh_token': token_data.get('refresh_token'),
            'name': account_info.get('name'),
            'phone': account_info.get('phone'),
            'profile_url': account_info.get('profile_url'),
        }
    )

    return avito_account


def refresh_token(avito_account: AvitoAccount):
    url = 'https://api.avito.ru/token/'
    data = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': avito_account.refresh_token
    }

    response = httpx_helper.request(
        method="POST",
        url=url,
        data=data,
    )
    response.raise_for_status()
    response_data = response.json()

    avito_account.access_token = response_data['access_token']
    avito_account.refresh_token = response_data['refresh_token']
    avito_account.save()

    return True
