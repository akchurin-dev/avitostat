from django.db import models
from django.contrib.auth.models import User
from avito_account.models.models import AvitoAccount


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
