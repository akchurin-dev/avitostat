from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from dateutil.parser import parse
from avito_account.models.models import BaseModel, AvitoAccount


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
        return f'{self.balance_tokens} , {self.status}'

    class Meta:
        verbose_name = "Пополнение"
        verbose_name_plural = "Пополнения"

    def update_by_object(object: dict):
        try:
            payment = Payment.objects.get(uuid=object.get("id"))
        except ObjectDoesNotExist:
            return
        # Обновление полей платежа с проверкой на наличие значений
        payment.status = object.get("status", payment.status)  # Оставляем текущее значение, если нет нового
        payment.currency = object.get("amount", {}).get("currency", payment.currency)
        payment.amount = float(object.get("amount", {}).get("value", payment.amount))
        payment.income_amount = float(object.get("income_amount", {}).get("value", payment.income_amount))

        payment.payment_method = object.get("payment_method", {}).get("type", payment.payment_method)

        payment.created_at = parse(object.get("created_at", payment.created_at))  # Дата создания платежа
        payment.updated_at = parse(object.get("captured_at", payment.updated_at))  # Дата списания платежа

        payment.test = bool(object.get("test", payment.test))  # Оставляем текущее значение, если нет нового
        payment.paid = bool(object.get("paid", payment.paid))  # Оставляем текущее значение, если нет нового

        # Установка URL подтверждения, если он присутствует
        if "confirmation_url" in object:
            payment.confirmation_url = object.get("confirmation_url")

        payment.description = object.get("description",
                                         payment.description)  # Оставляем текущее значение, если нет нового

        payment.save()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.FloatField(default=0)

    def __str__(self):
        return f"{self.user.username} - баланс {self.balance}"

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профиль"

    def update_balance_by_object(object: dict):
        #TODO Если необходимо можно реализовать логику зависящую от BalanceHistory.type(+/-)
        payment = Payment.objects.get(uuid=object.get("id"))
        user_profile = UserProfile.objects.get_or_create(user_id=payment.created_by.id)[0]
        user_profile.balance += payment.balance_tokens
        user_profile.save()

        BalanceHistory.objects.create(
            user_profile=user_profile,
            payment=payment,
            type=BalanceHistory.BALANCE_INCOMING,
            amount_tokens=payment.balance_tokens
        )

    async def waste_of_balance(avito_account: AvitoAccount, balance_decrease: int, test_from_prod: bool):
        if not test_from_prod:
            user_profile = await sync_to_async(UserProfile.objects.get)(user_id=avito_account.created_by_id)
            user_profile.balance -= balance_decrease
            await user_profile.asave()


class BalanceHistory(models.Model):
    BALANCE_INCOMING = 'incoming'
    BALANCE_OUTGOING = 'outgoing'

    BALANCE_HISTORY_TYPE_CHOICES = (
        ('incoming', 'Пополнение'),
        ('outgoing', 'Списание'),
    )

    avito_account = models.ForeignKey(AvitoAccount, on_delete=models.CASCADE, blank=True, null=True, )
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)  # for inline viewing in UserProfileAdmin
    type = models.CharField(max_length=30, choices=BALANCE_HISTORY_TYPE_CHOICES,
                            verbose_name="Тип действия")
    amount_tokens = models.FloatField(default=0, verbose_name="Сумма")

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, blank=True, null=True)
    sending_report = models.ForeignKey('avito_account.SendingReport', on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Операция с балансом"
        verbose_name_plural = "Операции с балансом"

    # def clean(self):
    #     # Проверяем, что заполнено одно и только одно из полей: либо payment, либо sending_report
    #     if (self.payment and self.sending_report) or (not self.payment and not self.sending_report):
    #         raise ValidationError("Укажите либо 'payment', либо 'sending_report', но не оба одновременно.")
    #
    #     # Проверка, если указан платёж, то поле avito_account должно быть пустым
    #     if self.payment and self.avito_account:
    #         raise ValidationError("Если указан платёж, поле 'Avito аккаунт' должно быть пустым.")
    #
    #     # Проверка, если указана рассылка, то поле avito_account обязательно должно быть заполнено
    #     if self.sending_report and not self.avito_account:
    #         raise ValidationError("Если указана рассылка, поле 'Avito аккаунт' должно быть заполнено.")

    # def save(self, *args, **kwargs):
    #     # Вызываем метод clean() перед сохранением
    #     self.clean()
    #     super().save(*args, **kwargs)
