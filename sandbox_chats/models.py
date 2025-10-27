from __future__ import annotations

from django.db import models
from django.db.models.query import QuerySet


class InputChat(models.Model):
    title = models.CharField(
        verbose_name="Название",
        max_length=255,
        blank=True,
    )

    answer_requirements = models.TextField(
        verbose_name="Требования к ответу",
        blank=True,
    )

    class Meta:
        verbose_name = "Тестовый чат"
        verbose_name_plural = "Тестовые чаты"

    def __str__(self) -> str:
        return self.title or f"Тестовый чат ({self.pk})"


class BaseSandboxSessionChat(models.Model):
    mark = models.SmallIntegerField(
        verbose_name="Оценка",
        null=True,
        default=None,
    )

    template_chat_id: int
    template_chat = models.ForeignKey(
        verbose_name="Основано на чате",
        to=InputChat,
        on_delete=models.CASCADE,
        null=True,
        default=None,
    )

    class Meta:
        abstract = True


class MessageRole(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Клиент"
    MANAGER = "MANAGER", "Менеджер"


class BaseMessage(models.Model):
    author = models.CharField(
        verbose_name="Автор",
        max_length=31,
        choices=MessageRole.choices,
    )

    text = models.TextField(
        verbose_name="Текст",
        blank=True,
    )

    image_url = models.TextField(
        verbose_name="URL изображения",
        blank=True,
    )

    created_at = models.DateTimeField(
        verbose_name="Создано",
        auto_now_add=True,
    )

    class Meta:
        abstract = True

    @property
    def from_customer(self) -> bool:
        return self.author == MessageRole.CUSTOMER.value

    @property
    def from_manager(self) -> bool:
        return not self.from_customer


class InputChatMessage(BaseMessage):
    chat_id: int
    chat = models.ForeignKey(
        verbose_name="Чат",
        to=InputChat,
        on_delete=models.CASCADE,
    )

    @staticmethod
    def get_messages_by_chat(chat_id: int) -> QuerySet[InputChatMessage]:
        return InputChatMessage.objects.filter(chat_id=chat_id)
