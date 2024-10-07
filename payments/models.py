# payments/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone


class Payment(models.Model):
    ORDER_STATUS_CHOICES = (
        ('succeeded', 'Оплачен'),
        ('canceled', 'Отменен'),
        ('waiting_for_capture', 'Ожидание'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='RUB')
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    description = models.TextField(null=True, blank=True)  # Дополнительное описание платежа
    confirmation_url = models.URLField(max_length=255, blank=True, null=True)  # Ссылка для подтверждения оплаты
