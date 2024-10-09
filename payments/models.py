# payments/models.py
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Payment(models.Model):
    PAYMENT_STATUS_PENDING = 'payment.pending'
    PAYMENT_STATUS_CANCELED = 'payment.canceled'
    PAYMENT_STATUS_WAITING_FOR_CAPTURE = 'payment.waiting_for_capture'
    PAYMENT_STATUS_SUCCEEDED = 'payment.succeeded'

    PAYMENT_STATUS_CHOICES = (
        ('payment.pending', 'Ожидание'),
        ('payment.canceled', 'Отменен'),
        ('payment.waiting_for_capture', 'Ожидание списания'),
        ('payment.succeeded', 'Оплачен'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    uuid = models.CharField(max_length=50, blank=True, null=True, editable=False)

    status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING)
    currency = models.CharField(max_length=3, default='RUB')
    amount = models.FloatField(blank=True, null=True)
    income_amount = models.FloatField(blank=True, null=True)

    payment_method = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    test = models.BooleanField(default=False)
    paid = models.BooleanField(default=False)
    confirmation_url = models.URLField(max_length=255, blank=True, null=True)  # Ссылка для подтверждения оплаты
    description = models.TextField(null=True, blank=True)  # Дополнительное описание платежа


    def __str__(self):
        return f'{self.user.username} - {self.status}'

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
