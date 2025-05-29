from django.db import models

import amo.models
from avito_account.models.models import AvitoAccount


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
