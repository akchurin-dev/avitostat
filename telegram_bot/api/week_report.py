import os

import requests
from dotenv import load_dotenv

from exceptions import HTTPException

load_dotenv()

BASE_URL = 'http://' + os.getenv('LOCALHOST_IP')


def get_week_report_by_telegram_id(telegram_chat_id: int):
    url = f"{BASE_URL}/conversion/week_report/{telegram_chat_id}"
    response = requests.get(url=url)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)


def get_duration_report_by_telegram_id(telegram_chat_id: int):
    url = f"{BASE_URL}/messaging/week_report/{telegram_chat_id}"
    response = requests.get(url=url, timeout=360)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)
