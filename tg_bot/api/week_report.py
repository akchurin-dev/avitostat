from base import settings
from utils import httpx_helper


BASE_URL = 'http://' + settings.LOCALHOST_IP


def get_pdf_report_all_to_users():
    url = f"{BASE_URL}/messaging/bad_messaging_week_report_all_to_users/"
    response = httpx_helper.request("GET", url)
    return response.json()


def get_pdf_report_all_to_admin():
    url = f"{BASE_URL}/deep_tests/bad_messaging_week_report_all_to_admin/"
    response = httpx_helper.request("GET", url)
    return response.json()
