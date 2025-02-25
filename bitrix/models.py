from typing import Iterable

from asgiref.sync import async_to_sync
from django.db import models
from django.contrib.auth.models import User

from bitrix.utils import openlines as bitrix_openlines
from chat_bot.models import AIChatBotBase


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

    access_token = models.TextField(
        verbose_name="Access-токен",
    )

    refresh_token = models.TextField(
        verbose_name="Токен обновления",
    )

    class Meta:
        verbose_name = "Аккаунт Битрикс24"
        verbose_name_plural = "Аккаунты Битрикс24"


# В дальнейшем добавим поля для связи бота с определенной воронкой

class AIChatBot(AIChatBotBase):
    bitrix_account = models.ForeignKey(
        to=BitrixAccount,
        on_delete=models.CASCADE,
        verbose_name="Битрикс-аккаунт",
    )

    class Meta:
        verbose_name = "Чат-бот"
        verbose_name_plural = "Чат-боты"

    def save(self, force_insert=False, force_update=False, using: str | None = None, update_fields: Iterable[str] | None = None) -> None:
        any_enabled_before_save = AIChatBot.objects.filter(
            bitrix_account__domain=self.bitrix_account.domain,
            is_active=True,
        ).exists()

        super().save(force_insert, force_update, using, update_fields)

        any_enabled_after_save = AIChatBot.objects.filter(
            bitrix_account__domain=self.bitrix_account.domain,
            is_active=True,
        ).exists()

        if any_enabled_before_save and not any_enabled_after_save:
            async_to_sync(bitrix_openlines.disable_bot)(self.bitrix_account.domain)

        if not any_enabled_before_save and any_enabled_after_save:
            async_to_sync(bitrix_openlines.activate_bot)(self.bitrix_account.domain)
