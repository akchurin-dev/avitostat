import unittest
from unittest.mock import patch
from payments.services import YookassaService


class TestYookassaService(unittest.TestCase):
    def setUp(self):
        self.service = YookassaService()
        self.order_id = 'test_order_123'
        self.amount = 100.0
        self.currency = 'RUB'
        self.description = 'Тестовый платеж'
        self.return_url = 'https://example.com/success'

    @patch('payments.services.requests.post')
    def test_create_payment(self, mock_post):
        # Задаем ожидаемый ответ от API
        mock_response = {
            "id": "test_payment_id",
            "status": "pending",
            "confirmation": {"confirmation_url": "https://example.com/confirmation"}
        }
        mock_post.return_value.json.return_value = mock_response

        # Тестирование создания платежа
        response = self.service.create_payment(
            self.amount, self.currency, self.description, self.order_id, self.return_url
        )
        self.assertEqual(response['id'], "test_payment_id")
        self.assertEqual(response['status'], "pending")
        self.assertIn("confirmation_url", response["confirmation"])

    @patch('payments.services.requests.get')
    def test_get_payment_status(self, mock_get):
        # Задаем ожидаемый ответ от API
        mock_response = {"id": "test_payment_id", "status": "paid"}
        mock_get.return_value.json.return_value = mock_response

        # Тестирование получения статуса платежа
        response = self.service.get_payment_status("test_payment_id")
        self.assertEqual(response['status'], "paid")
