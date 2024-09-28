from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from payments.models import Payment


class PaymentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.create_payment_url = reverse('create_payment')
        self.check_status_url = lambda order_id: reverse('check_payment_status', args=[order_id])
        # self.webhook_url = reverse('webhook_handler')

        # Тестовый платеж
        self.payment = Payment.objects.create(
            order_id='test_order_123',
            amount=100.0,
            status='pending',
            confirmation_url='https://example.com/confirmation'
        )

    @patch('payments.services.YookassaService.create_payment')
    def test_create_payment_view(self, mock_create_payment):
        # Задаем возвращаемое значение от mock-метода
        mock_create_payment.return_value = {
            "id": "test_payment_id",
            "status": "pending",
            "confirmation": {"confirmation_url": "https://example.com/confirmation"}
        }

        response = self.client.get(self.create_payment_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://example.com/confirmation")

        # Проверка, что платеж сохранен в базе данных
        payment = Payment.objects.get(order_id='test_order_123')
        self.assertEqual(payment.status, 'pending')

    @patch('payments.services.YookassaService.get_payment_status')
    def test_check_payment_status_view(self, mock_get_payment_status):
        # Задаем возвращаемое значение от mock-метода
        mock_get_payment_status.return_value = {"status": "paid"}

        response = self.client.get(self.check_status_url('test_order_123'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'paid'})

        # Проверка, что статус обновлен в базе данных
        payment = Payment.objects.get(order_id='test_order_123')
        self.assertEqual(payment.status, 'paid')

    # def test_webhook_handler_view(self):
    #     # Тестирование обработки вебхуков
    #     webhook_data = {
    #         "event": "payment.succeeded",
    #         "object": {
    #             "metadata": {"order_id": "test_order_123"},
    #             "status": "paid"
    #         }
    #     }
    #     response = self.client.post(self.webhook_url, data=webhook_data, content_type='application/json')
    #     self.assertEqual(response.status_code, 200)
    #
    #     # Проверка, что статус обновлен в базе данных
    #     payment = Payment.objects.get(order_id='test_order_123')
    #     self.assertEqual(payment.status, 'paid')
