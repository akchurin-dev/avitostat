import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = 'http://' + os.getenv('LOCALHOST_IP')


def get_pdf_report_all_to_users():
    url = f"{BASE_URL}/messaging/bad_messaging_week_report_all_to_users/"
    response = requests.get(url=url)
    return response.json()


def get_pdf_report_all_to_admin():
    url = f"{BASE_URL}/deep_tests/bad_messaging_week_report_all_to_admin/"
    response = requests.get(url=url)
    return response.json()
