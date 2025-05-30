from typing import Any, Iterable
from django.db import models

import amo.models
from avito_account.models.models import AvitoAccount
from avito_account.utils import avito_webhooks


class AmoAvitoAccountsLink(models.Model):
    is_active = models.BooleanField(
        verbose_name="Активно",
        default=True,
    )

    amo_account = models.ForeignKey(
        verbose_name="Амо-аккаунт",
        to=amo.models.AmoAccount,
        on_delete=models.CASCADE,
    )

    avito_account = models.ForeignKey(
        verbose_name="Авито-аккаунт",
        to=AvitoAccount,
        on_delete=models.PROTECT,
        unique=True,
    )

    class Meta:
        verbose_name = "Связь аккаунтов Амо-Авито"
        verbose_name_plural = "Связи аккаунтов Амо-Авито"

    def save(self, force_insert: bool, force_update: bool, using: str | None, update_fields: Iterable[str] | None) -> None:
        super().save(force_insert, force_update, using, update_fields)
        avito_webhooks.update_avito_webhook_subscription(self.avito_account)

    def delete(self, using: Any, keep_parents: bool) -> tuple[int, dict[str, int]]:
        avito_webhooks.update_avito_webhook_subscription(self.avito_account)
        return super().delete(using, keep_parents)


class AmoContactAvitoChatLink(models.Model):
    amo_account = models.ForeignKey(
        verbose_name="Амо-аккаунт",
        to=amo.models.AmoAccount,
        on_delete=models.CASCADE,
    )

    contact_id = models.BigIntegerField(
        verbose_name="Идентификатор контакта в системе амо",
        db_index=True,
    )

    avito_account = models.ForeignKey(
        verbose_name="Авито-аккаунт",
        to=AvitoAccount,
        on_delete=models.PROTECT,
    )

    chat_id = models.CharField(
        verbose_name="Идентфикатор чата в системе Авито",
        max_length=255,
        db_index=True,
    )

    class Meta:
        verbose_name = "Связь Амо-Контакт - Авито-Чат"
        verbose_name_plural = "Связи Амо-Контакт - Авито-Чат"

        unique_together = [
            ("amo_account", "contact_id"),
            ("avito_account", "chat_id"),
        ]
