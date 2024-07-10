import os

import requests
from django.http import JsonResponse
from dotenv import load_dotenv

from exceptions import HTTPException

load_dotenv()

BASE_URL = 'http://' + os.getenv('LOCALHOST_IP')


def get_avito_account_data_by_telegram_id(telegram_id: int):
    url = f"{BASE_URL}/oauth/avito_account_by_telegram_id/{telegram_id}"
    response = requests.get(url=url)
    return response.json()


def get_avito_account_all_ids():
    url = f"{BASE_URL}/oauth/avito_accounts_list/"
    response = requests.get(url=url)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)


def get_week_report_by_id(avito_account_id: int):
    url = f"{BASE_URL}/conversion/week_report/{avito_account_id}"
    response = requests.get(url=url)
    return response.json()


def get_duration_report_by_telegram_id(avito_account_id: int):
    url = f"{BASE_URL}/messaging/week_report/{avito_account_id}"
    response = requests.get(url=url, timeout=360)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)
