from asgiref.sync import async_to_sync
from django.db import models
from django.contrib.auth.models import User
from avito_account.models.models import AvitoAccount
from chat_bot.api.subscriptions import subscribe_to_messages, stop_subscribe_to_messages


class AiChatBot(models.Model):
    avito_account = models.OneToOneField(
        AvitoAccount,
        on_delete=models.CASCADE,
        related_name='ai_chat_bots',
        verbose_name="ИИ чат бот"
    )

    is_active = models.BooleanField(default=False, verbose_name="Активирован")
    total_info = models.TextField(verbose_name="Общая информация")
    rules = models.TextField(verbose_name="Правила при общении")
    checkpoints = models.TextField(verbose_name="Шаги при общении")

    class Meta:
        verbose_name = "ИИ чат бот"
        verbose_name_plural = "ИИ чат боты"

    def save(self, *args, **kwargs):
        previous = AiChatBot.objects.filter(pk=self.pk).last()
        # Сначала сохраняем объект
        super().save(*args, **kwargs)

        if previous is None:  # Если изначально вообще небыло инстанса
            if self.is_active:
                async_to_sync(subscribe_to_messages)(self.avito_account)
        else:
            if previous.is_active != self.is_active:
                if self.is_active:
                    async_to_sync(subscribe_to_messages)(self.avito_account)
                else:
                    async_to_sync(stop_subscribe_to_messages)(self.avito_account)

    def delete(self, using=None, keep_parents=False):
        if self.is_active:
            async_to_sync(stop_subscribe_to_messages)(self.avito_account)
        super().delete()
