from django.contrib.auth.models import User
from django.db import models

from chat_bot import models as avito_models


class Task(avito_models.AIChatBotTaskBase):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        PREPARING_DATA = "PREPARING_DATA"
        ANSWER_GENERATION = "ANSWER_GENERATION"
        ANSWER_SENDING = "ANSWER_SENDING"
        FINISHED = "FINISHED"
        CANCELED = "CANCELED"

    owner = models.ForeignKey(
        to=User,
        on_delete=models.CASCADE,
        verbose_name="Владелец",
    )
    
    chat_id = models.CharField(
        verbose_name="Идентификатор чата",
        max_length=255,
    )

    status = models.CharField(
        verbose_name="Статус",
        choices=Status,
        default=Status.PENDING.value,
    )

    class Meta:
        verbose_name = "Задача чат-бота"
        verbose_name_plural = "Задачи чат-ботов"
