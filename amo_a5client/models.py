from django.db import models
from django.db.models.functions import Abs

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

    avito_account = models.OneToOneField(
        verbose_name="Авито-аккаунт",
        to=AvitoAccount,
        on_delete=models.PROTECT,
    )

    class Meta:
        verbose_name = "Связь аккаунтов Амо-Авито"
        verbose_name_plural = "Связи аккаунтов Амо-Авито"

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        avito_webhooks.update_avito_webhook_subscription(self.avito_account)

    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:
        avito_webhooks.update_avito_webhook_subscription(self.avito_account)
        return super().delete(*args, **kwargs)


# class AmoContactAvitoChatLink(models.Model):
#     amo_account = models.ForeignKey(
#         verbose_name="Амо-аккаунт",
#         to=amo.models.AmoAccount,
#         on_delete=models.CASCADE,
#     )

#     contact_id = models.BigIntegerField(
#         verbose_name="Идентификатор контакта в системе амо",
#         db_index=True,
#     )

#     avito_account = models.ForeignKey(
#         verbose_name="Авито-аккаунт",
#         to=AvitoAccount,
#         on_delete=models.PROTECT,
#     )

#     chat_id = models.CharField(
#         verbose_name="Идентфикатор чата в системе Авито",
#         max_length=255,
#         db_index=True,
#     )

#     class Meta:
#         verbose_name = "Связь Амо-Контакт - Авито-Чат"
#         verbose_name_plural = "Связи Амо-Контакт - Авито-Чат"

#         unique_together = [
#             ("amo_account", "contact_id"),
#             ("avito_account", "chat_id"),
#         ]


# TODO временное решение, хранить связи в редисе или где-то в другом месте
class MessageContactLink(models.Model):
    message_created_at = models.IntegerField(db_index=True)
    text = models.TextField()
    author_name = models.TextField()

    amo_account_id = models.IntegerField()
    contact_id = models.IntegerField(null=True, default=None)

    avito_account_id = models.IntegerField(null=True, default=None)
    avito_chat_id = models.CharField(max_length=63, null=True, default=None)
    avito_message_id = models.CharField(max_length=63, null=True, default=None)

    @classmethod
    def get_or_create_by_amo_data(
        cls,
        message_created_at_ts: int,
        text: str,
        author_name: str,
        amo_account_id: int,
        amo_contact_id: int,
    ):
        link = (
            cls.objects.annotate(
                created_at_diff=Abs(models.F("message_created_at") - models.Value(message_created_at_ts))
            ).filter(
                created_at_diff__lte=5,
                text=text,
                author_name=author_name,
                amo_account_id=amo_account_id,
            )
            .order_by("message_created_at")
            .last()
        )

        if link:
            return link

        link = cls.objects.create(
            message_created_at=message_created_at_ts,
            text=text,
            author_name=author_name,
            amo_account_id=amo_account_id,
            contact_id=amo_contact_id,
        )

        return link

    @classmethod
    def get_or_create_by_avito_data(
        cls,
        message_created_at_ts: int,
        text: str,
        author_name: str,
        amo_account_id: int,
        avito_account_id: int,
        avito_chat_id: str,
        avito_message_id: str
    ):
        link = (
            cls.objects
            .annotate(
                created_at_diff=Abs(models.F("message_created_at") - models.Value(message_created_at_ts))
            )
            .filter(
                created_at_diff__lte=5,
                text=text,
                author_name=author_name,
                amo_account_id=amo_account_id,
            )
            .order_by("message_created_at")
            .last()
        )

        if link:
            return link

        link = cls.objects.create(
            message_created_at=message_created_at_ts,
            text=text,
            author_name=author_name,
            amo_account_id=amo_account_id,
            avito_account_id=avito_account_id,
            avito_chat_id=avito_chat_id,
            avito_message_id=avito_message_id,
        )

        return link
