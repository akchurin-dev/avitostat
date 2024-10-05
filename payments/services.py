# payments/services.py
import uuid

import requests
from django.conf import settings


class YookassaService:
    def __init__(self):
        self.base_url = "https://api.yookassa.ru/v3/"
        self.auth = (settings.YOOKASSA_TEST_SHOP_ID, settings.YOOKASSA_TEST_SECRET_KEY)
        self.headers = {
            'Idempotence-Key': str(uuid.uuid4())
        }

    def create_payment(self, amount, currency, description, order_id, return_url):
        payload = {
            "amount": {"value": str(amount), "currency": currency},
            "description": description,
            "confirmation": {"type": "redirect", "return_url": "https://avitostata.ru/admin"},
            "capture": True,
            "metadata": {"order_id": order_id},
        }
        response = requests.post(
            url=f"{self.base_url}payments",
            headers=self.headers,
            json=payload,
            auth=self.auth
        )
        return response.json()

    def get_payment_status(self, payment_id):
        response = requests.get(
            url=f"{self.base_url}payments/{payment_id}",
            auth=self.auth
        )
        return response.json()
