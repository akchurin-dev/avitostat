from django.contrib.auth.models import User
from django.db import models

from avito_account.models.models import BaseModel, AvitoAccount


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.FloatField(default=0)

    def __str__(self):
        return f"{self.user.username} - баланс {self.balance}"

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профиль"


class BalanceHistory(models.Model):
    BALANCE_INCOMING = 'incoming'
    BALANCE_OUTGOING = 'outgoing'

    BALANCE_HISTORY_TYPE_CHOICES = (
        ('incoming', 'Пополнение'),
        ('outgoing', 'Списание'),
    )

    avito_account = models.ForeignKey(AvitoAccount, on_delete=models.CASCADE)
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    type = models.CharField(max_length=30, choices=BALANCE_HISTORY_TYPE_CHOICES,
                            verbose_name="Тип действия")
    amount = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class Payment(BaseModel):
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

    uuid = models.CharField(max_length=50, blank=True, null=True, editable=False, verbose_name="Уникальный номер")

    status = models.CharField(max_length=30, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING,
                              verbose_name="Статус платежа")
    currency = models.CharField(max_length=3, default='RUB', verbose_name="Валюта")
    amount = models.FloatField(blank=True, null=True, verbose_name="Сумма к списанию")
    income_amount = models.FloatField(blank=True, null=True, verbose_name="Сумма получена")
    balance_tokens = models.IntegerField(default=0, verbose_name="Токенов к зачислению")

    payment_method = models.CharField(max_length=50, null=True, blank=True, verbose_name="Метод оплаты")
    created_at = models.DateTimeField(null=True, verbose_name="Cоздан платёж")
    updated_at = models.DateTimeField(null=True, verbose_name="Списана сумма")

    test = models.BooleanField(default=False, verbose_name="Тест")
    paid = models.BooleanField(default=False, verbose_name="Оплачено")
    confirmation_url = models.URLField(max_length=255, blank=True, null=True,
                                       verbose_name="Ссылка для оплаты")  # Ссылка для подтверждения оплаты
    description = models.TextField(null=True, blank=True,
                                   verbose_name="Описание платежа")  # Дополнительное описание платежа

    def __str__(self):
        return f'{self.created_by.username}'

    class Meta:
        verbose_name = "Пополнение"
        verbose_name_plural = "Пополнения"
