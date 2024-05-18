import os
from pprint import pprint

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = 'http://' + os.getenv('LOCALHOST_IP')


# WORKER
def get_week_report_by_telegram_id(telegram_chat_id: int):
    url = f"{BASE_URL}/conversion/week_report/{telegram_chat_id}"
    response = requests.get(url=url)
    return response.json()
