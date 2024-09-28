from django.test import TestCase
from payments.models import Payment


class PaymentModelTests(TestCase):
    def test_create_payment(self):
        # Создаем новый платеж и проверяем его поля
        payment = Payment.objects.create(
            order_id='order_123',
            amount=200.00,
            status='pending',
            confirmation_url='https://example.com/confirm'
        )
        self.assertEqual(payment.order_id, 'order_123')
        self.assertEqual(payment.amount, 200.00)
        self.assertEqual(payment.status, 'pending')
        self.assertEqual(payment.confirmation_url, 'https://example.com/confirm')

    def test_update_payment_status(self):
        # Проверка обновления статуса платежа
        payment = Payment.objects.create(
            order_id='order_124',
            amount=150.00,
            status='pending'
        )
        payment.status = 'paid'
        payment.save()
        self.assertEqual(payment.status, 'paid')
