from typing import Iterable

from django.db import models
from django.contrib.auth.models import User

from bitrix.utils import openlines as bitrix_openlines
from chat_bot import models as avito_models


class BitrixAccount(models.Model):
    # Домен в формате "abc123.bitrix.com" или "abc123.bitrix.ru", без косых черт и без https
    domain = models.CharField(
        verbose_name="Домен",
        max_length=255,
        primary_key=True,
    )

    owner = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        related_name="bitrix_account",
        verbose_name="Владелец аккаунта",
    )

    telegram_id = models.CharField(
        verbose_name="Telegram ID",
        max_length=255,
        null=True,
    )

    access_token = models.TextField(
        verbose_name="Access-токен",
        null=True,
    )

    refresh_token = models.TextField(
        verbose_name="Токен обновления",
        null=True,
    )

    class Meta:
        verbose_name = "Аккаунт Битрикс24"
        verbose_name_plural = "Аккаунты Битрикс24"


# В дальнейшем добавим поля для связи бота с определенной воронкой

class BitrixAIChatBot(avito_models.AIChatBotBase):
    bitrix_account = models.ForeignKey(
        to=BitrixAccount,
        on_delete=models.CASCADE,
        verbose_name="Битрикс-аккаунт",
    )

    class Meta:
        verbose_name = "Чат-бот"
        verbose_name_plural = "Чат-боты"

    def save(self, force_insert=False, force_update=False, using: str | None = None, update_fields: Iterable[str] | None = None) -> None:
        any_enabled_before_save = BitrixAIChatBot.objects.filter(
            bitrix_account__domain=self.bitrix_account.domain,
            is_active=True,
        ).exists()

        super().save(force_insert, force_update, using, update_fields)

        any_enabled_after_save = BitrixAIChatBot.objects.filter(
            bitrix_account__domain=self.bitrix_account.domain,
            is_active=True,
        ).exists()

        if any_enabled_before_save and not any_enabled_after_save:
            bitrix_openlines.disable_bot(self.bitrix_account.domain)

        if not any_enabled_before_save and any_enabled_after_save:
            bitrix_openlines.activate_bot(self.bitrix_account.domain)
