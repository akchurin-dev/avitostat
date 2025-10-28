from __future__ import annotations

from django.db import models
from django.db.models.query import QuerySet

from utils import universal_messages
from utils.miscellaneous import datetime_now_msk


class SandboxSessionStatus(models.TextChoices):
    CREATED = "CREATED", "Создано"
    IN_PROGRESS = "IN PROGRESS", "Выполняется"
    INTERRUPTED = "INTERRUPTED", "Прервано"
    FINISHED = "FINISHED", "Завершено"


class SandboxSession(models.Model):
    status = models.CharField(
        verbose_name="Статус",
        max_length=31,
        choices=SandboxSessionStatus.choices,
        default=SandboxSessionStatus.CREATED,
    )

    created_at = models.DateTimeField(
        verbose_name="Создано",
        default=datetime_now_msk,
    )

    class Meta:
        verbose_name = "Тестовая сессия"
        verbose_name_plural = "Тестовые сессии"

    def mark_as_inprogress(self, save: bool = False) -> None:
        self.set_status(SandboxSessionStatus.IN_PROGRESS, save)

    def mark_as_interrupted(self, save: bool) -> None:
        self.set_status(SandboxSessionStatus.INTERRUPTED, save)

    def mark_as_finished(self, save: bool) -> None:
        self.set_status(SandboxSessionStatus.FINISHED, save)

    def set_status(self, status, save: bool) -> None:
        self.status = status

        if save:
            self.save()


class SandboxBaseChat(models.Model):
    answer_requirements = models.TextField(
        verbose_name="Требования к ответу",
        blank=True,
    )

    created_at = models.DateTimeField(
        verbose_name="Создано",
        default=datetime_now_msk,
    )

    class Meta:
        abstract = True


class SandboxInputChat(SandboxBaseChat):
    title = models.CharField(
        verbose_name="Название",
        max_length=255,
        blank=True,
    )

    class Meta:
        verbose_name = "Тестовый чат"
        verbose_name_plural = "Тестовые чаты"

    def __str__(self) -> str:
        return self.title or f"Тестовый чат ({self.pk})"


class SandboxSessionInputChatLink(models.Model):
    session_id: int
    session = models.ForeignKey(
        verbose_name="Тестовая сессия",
        to=SandboxSession,
        on_delete=models.CASCADE,
    )

    chat_id: int
    chat = models.ForeignKey(
        verbose_name="Тестовый чат",
        to=SandboxInputChat,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Связь Тестовая сессия - Тестовый чат"
        verbose_name_plural = "Связи Тестовая сессия - Тестовый чат"

    @staticmethod
    def instantiate(session_id: int, chat_id: int) -> SandboxSessionInputChatLink:
        link = SandboxSessionInputChatLink()

        link.session_id = session_id
        link.chat_id = chat_id

        return link


class SandboxOutputChat(SandboxBaseChat):
    session_id: int
    session = models.ForeignKey(
        verbose_name="Тестовая сессия",
        to=SandboxSession,
        on_delete=models.CASCADE,
    )

    input_chat_id: int
    input_chat = models.ForeignKey(
        verbose_name="Основано на чате",
        to=SandboxInputChat,
        on_delete=models.CASCADE,
        null=True,
        default=None,
    )

    avg_rate = models.FloatField(
        verbose_name="Средняя оценка",
        null=True,
        default=None,
    )

    min_rate = models.SmallIntegerField(
        verbose_name="Минимальная оценка",
        null=True,
        default=None,
    )
    
    max_rate = models.SmallIntegerField(
        verbose_name="Максимальная оценка",
        null=True,
        default=None,
    )

    class Meta:
        verbose_name = "Выходной тестовый чат"
        verbose_name_plural = "Выходные тестовые чаты"

    @staticmethod
    def instantiate(session_id: int, input_chat: SandboxInputChat) -> SandboxOutputChat:
        chat = SandboxOutputChat()

        chat.session_id = session_id
        chat.input_chat = input_chat
        chat.answer_requirements = input_chat.answer_requirements

        return chat


class BaseSandboxAnswer(models.Model):
    chat_id: int
    chat = models.ForeignKey(
        verbose_name="Тестовый чат",
        to=SandboxOutputChat,
        on_delete=models.CASCADE,
    )

    rate = models.SmallIntegerField(
        verbose_name="Оценка",
    )

    rate_explanation = models.TextField(
        verbose_name="Пояснение к оценке",
    )

    class Meta:
        verbose_name = "Ответ на тест"
        verbose_name = "Ответы на тесты"

        abstract = True


class SandboxTextAnswer(BaseSandboxAnswer):
    text = models.TextField(
        verbose_name="Текст",
    )

    @staticmethod
    def instantiate(chat_id: int, text: str, rate: int, rate_explanation: str) -> SandboxTextAnswer:
        answer = SandboxTextAnswer()

        answer.chat_id = chat_id
        answer.text = text
        answer.rate = rate
        answer.rate_explanation = rate_explanation

        return answer


class MessageRole(models.TextChoices):
    CUSTOMER = "CUSTOMER", "Клиент"
    MANAGER = "MANAGER", "Менеджер"


class ChatMessage(models.Model):
    input_chat_id: int
    input_chat = models.ForeignKey(
        verbose_name="Входной чат",
        to=SandboxInputChat,
        on_delete=models.CASCADE,
        null=True,
    )

    output_chat_id: int
    output_chat = models.ForeignKey(
        verbose_name="Выходной чат",
        to=SandboxOutputChat,
        on_delete=models.CASCADE,
        null=True,
    )

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
        default=datetime_now_msk,
    )

    class Meta:
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"

    @property
    def from_customer(self) -> bool:
        return self.author == MessageRole.CUSTOMER.value

    @property
    def from_manager(self) -> bool:
        return not self.from_customer

    def as_universal_format(self) -> universal_messages.Message:
        return universal_messages.Message(
            author="manager" if self.from_manager else "client",
            text=self.text,
            image_url=self.image_url,
        )

    @staticmethod
    def get_messages_by_input_chat(chat_id: int) -> QuerySet[ChatMessage]:
        return ChatMessage.objects.filter(input_chat_id=chat_id).order_by("created_at", "id")

    def copy_without_chat_id(self) -> ChatMessage:
        message = ChatMessage()

        message.author = self.author
        message.text = self.text
        message.image_url = self.image_url
        message.created_at = self.created_at

        return message
