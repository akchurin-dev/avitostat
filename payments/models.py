import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Payment(models.Model):
    PAYMENT_STATUS_PENDING = 'pending'
    PAYMENT_STATUS_CANCELED = 'canceled'
    PAYMENT_STATUS_WAITING_FOR_CAPTURE = 'waiting_for_capture'
    PAYMENT_STATUS_SUCCEEDED = 'succeeded'

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Ожидание'),
        ('canceled', 'Отменен'),
        ('waiting_for_capture', 'Ожидание списания'),
        ('succeeded', 'Оплачен'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Пользователь")
    uuid = models.CharField(max_length=50, blank=True, null=True, editable=False, verbose_name="Уникальный номер")

    status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING, verbose_name="Статус платежа")
    currency = models.CharField(max_length=3, default='RUB', verbose_name="Валюта")
    amount = models.FloatField(blank=True, null=True, verbose_name="Сумма списана")
    income_amount = models.FloatField(blank=True, null=True, verbose_name="Сумма получена")

    payment_method = models.CharField(max_length=50, null=True, blank=True, verbose_name="Метод оплаты")
    created_at = models.DateTimeField(null=True, verbose_name="Cоздан платёж")
    updated_at = models.DateTimeField(null=True, verbose_name="Списана сумма")

    test = models.BooleanField(default=False, verbose_name="Тест")
    paid = models.BooleanField(default=False, verbose_name="Оплачено")
    confirmation_url = models.URLField(max_length=255, blank=True, null=True, verbose_name="Ссылка для оплаты")  # Ссылка для подтверждения оплаты
    description = models.TextField(null=True, blank=True, verbose_name="Описание платежа")  # Дополнительное описание платежа


    def __str__(self):
        return f'{self.user.username} - {self.status}'

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
