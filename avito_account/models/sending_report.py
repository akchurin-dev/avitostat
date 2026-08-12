from django.db import models
from avito_account.models.models import AvitoAccount
from django.utils import timezone
from payments.models import UserProfile, BalanceHistory


class SendingCampaign(models.Model):  # Не BaseModel тк рассылки общие и мы их не можем привязывать к юзеру
    PDF = 'PDF'
    TEXT = 'TXT'

    SENDING_TYPE_CHOICES = [
        (PDF, 'PDF'),
        (TEXT, 'Text'),
    ]

    name = models.CharField(max_length=255, verbose_name="Название рассылки")
    test_from_prod = models.BooleanField(default=False, verbose_name="Тест")
    sending_type = models.CharField(max_length=3, choices=SENDING_TYPE_CHOICES, default=PDF,
                                    verbose_name="Тип рассылки")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Когда создано")

    accounts_presented_count = models.IntegerField(default=0, verbose_name="Аккаунтов к анализу")
    accounts_presented = models.ManyToManyField(AvitoAccount, related_name="campaigns_presented", blank=True,
                                                verbose_name="Аккаунты к анализу")

    auto_generated = models.BooleanField(default=False, verbose_name="Автоматически")

    class Meta:
        verbose_name = "Рассылка"
        verbose_name_plural = "Рассылки"

    def __str__(self):
        return f"Рассылка {self.name} ({self.get_sending_type_display()}) в {self.created_at}"


class SendingReport(models.Model):  # Не BaseModel тк репорпты должны привязываться к аккаунту а не к юзеру
    avito_account = models.ForeignKey('AvitoAccount', on_delete=models.CASCADE, verbose_name="Авито аккаунт")
    avito_account_name = models.CharField('Название Avito-аккаунт', max_length=255)
    campaign = models.ForeignKey('SendingCampaign', on_delete=models.CASCADE, related_name='reports',
                                 verbose_name="Рассылка")
    success = models.BooleanField(default=False, verbose_name="Успешно")
    error_message = models.CharField(null=True, blank=True, max_length=255, verbose_name="Сообщение ошибки")
    pdf_path = models.CharField(max_length=255, null=True, blank=True, verbose_name="Ссылка к пдф отчёту")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Дата создания")

    tokens_completion = models.IntegerField(default=0, verbose_name="Токены на вычисления")
    tokens_prompt = models.IntegerField(default=0, verbose_name="Токены на контекст")

    balance_decrease = models.IntegerField(default=0, verbose_name="К списанию с баланса")

    class Meta:
        verbose_name = "Отчёт о рассылке"
        verbose_name_plural = "отчёты о рассылках"

    def __str__(self):
        return f"Отчёт о рассылке для {self.avito_account_name} в {self.timestamp}"

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.avito_account_name = self.avito_account.name
        super().save(force_insert, force_update, using, update_fields)

        current_user_profile, _ = UserProfile.objects.get_or_create(user_id=self.avito_account.created_by_id)
        # TODO If there are multiple amounts for different deduction operations, additional logic will
        # TODO need to be implemented here.

        if self.balance_decrease > 0:
            BalanceHistory.objects.create(
                avito_account=self.avito_account,
                user_profile=current_user_profile,
                type=BalanceHistory.BALANCE_OUTGOING,
                amount_tokens=self.balance_decrease,
                sending_report=self,
            )
