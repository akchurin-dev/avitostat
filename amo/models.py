from django.contrib.auth.models import User
from django.db import models

from amo.utils import amo_chatbottasks
import chat_bot.models
from chatbottasks import chatbottasks


class AmoAccount(models.Model):
    amo_id = models.BigIntegerField(
        verbose_name="Идентификатор в системе amo",
        primary_key=True,
    )

    telegram_id = models.CharField(
        verbose_name="Идентификатор чата для отчетов",
        max_length=255,
        null=True,
        blank=True,
    )

    domain = models.CharField(
        verbose_name="Домен",
        unique=True,
        max_length=255,
    )

    amojo_id = models.CharField(
        verbose_name="Идентификатор в системе amojo",
        unique=True,
        max_length=255,
    )

    name = models.CharField(
        verbose_name="Название",
        max_length=255,
    )

    amo_login = models.CharField(
        verbose_name="Логин",
        max_length=255,
    )

    amo_password = models.TextField(
        verbose_name="Пароль",
    )

    access_token = models.TextField(
        verbose_name="Access-токен",
    )

    refresh_token = models.TextField(
        verbose_name="Refresh-токен",
    )

    amojo_access_token = models.TextField(
        verbose_name="Access-токен для amojo сервиса",
        null=True,
    )

    cookies_session_id = models.TextField(
        verbose_name="Id сессии для ajax запросов",
        null=True,
    )

    cookies_csrf_token = models.TextField(
        verbose_name="CSRF-токен для ajax запросов",
        null=True,
    )

    cookies_access_token = models.TextField(
        verbose_name="Access-токен для ajax запросов",
        null=True,
    )

    cookies_refresh_token = models.TextField(
        verbose_name="Refresh-токен для ajax запросов",
        null=True,
    )

    created_by = models.ForeignKey(
        verbose_name="Кем создан",
        to=User,
        on_delete=models.PROTECT,
    )

    created_at = models.DateTimeField(
        verbose_name="Когда создан",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        verbose_name="Когда обновлен",
        auto_now=True,
    )

    class Meta:
        verbose_name = "Amo-аккаунт"
        verbose_name_plural = "Amo-аккаунты"

    def __str__(self):
        return self.domain


class AmoChatBot(chat_bot.models.AIChatBotBase):
    account = models.ForeignKey(
        verbose_name="Amo-аккаунт",
        to=AmoAccount,
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        verbose_name="Имя бота",
        max_length=255,
        blank=True,
    )

    role_and_tasks = models.TextField(
        verbose_name="Роль и задачи",
        blank=True,
    )

    behaviour_style = models.TextField(
        verbose_name="Стиль поведения во время общения",
        blank=True,
    )

    company_and_products = models.TextField(
        verbose_name="Описание компании и продуктов",
        blank=True,
    )

    important_conditions = models.TextField(
        verbose_name="На какие важные условия боту обратить внимание",
        blank=True,
    )

    links_and_contacts = models.TextField(
        verbose_name="Полезные ссылки и контакты",
        blank=True,
    )

    class Meta:
        verbose_name = "Amo чат-бот"
        verbose_name_plural = "Amo чат-боты"

    def __str__(self):
        return f"{self.name} ({self.pk})"


class AmoEntity(models.TextChoices):
    CONTACT = "CONTACT", "Контакт"
    LEAD = "LEAD", "Сделка"


class FillableField(models.Model):
    chatbot = models.ForeignKey(
        verbose_name="Чат-бот заполнитель поля",
        to=AmoChatBot,
        on_delete=models.CASCADE,
    )

    name = models.CharField(
        verbose_name="Название",
        max_length=255,
    )

    entity = models.CharField(
        verbose_name="К чему относится поле",
        choices=AmoEntity.choices,
    )

    description = models.TextField(
        verbose_name="Описание поля для промпта",
    )

    class Meta:
        verbose_name = "Заполняемое поле"
        verbose_name_plural = "Заполняемые поля"


class AmoPipelineStatus(models.Model):
    account = models.ForeignKey(
        verbose_name="Amo-аккаунт",
        to=AmoAccount,
        on_delete=models.CASCADE,
    )

    pipeline_id = models.BigIntegerField(
        verbose_name="Идентификатор воронки в системе Amo",
        db_index=True,
    )

    pipeline_name = models.CharField(
        verbose_name="Название воронки",
        max_length=255,
    )

    amo_id = models.BigIntegerField(
        verbose_name="Идентификатор этапа в системе Amo",
        db_index=True,
    )

    name = models.CharField(
        verbose_name="Название этапа",
        max_length=255,
    )

    chat_bot = models.ForeignKey(
        verbose_name="Чат-бот обработчик сделок",
        to=AmoChatBot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Этап Amo-воронки"
        verbose_name_plural = "Этапы Amo-воронок"

        unique_together = ["account", "pipeline_id", "amo_id"]

    def __str__(self):
        return f"{self.pipeline_name} -> {self.name}"


class AmoChatBotTask(chat_bot.models.AIResultContainer, chatbottasks.Task):
    account = models.ForeignKey(
        verbose_name="Amo-аккаунт",
        to=AmoAccount,
        on_delete=models.CASCADE,
    )

    chatbot = models.ForeignKey(
        verbose_name="чат-бот",
        to=AmoChatBot,
        on_delete=models.SET_NULL,
        null=True,
    )

    lead_id = models.CharField(
        verbose_name="Идентификатор сделки",
        max_length=15,
        db_index=True,
    )

    chat_id = models.CharField(
        verbose_name="Идентификатор чата",
        max_length=255,
        db_index=True,
    )

    # В рамках одного чата может быть много разговоров.
    # На каждую новую сделку создается новый разговор
    talk_id = models.IntegerField(
        verbose_name="Идентификатор разговора",
        db_index=True,
    )

    message_id = models.CharField(
        verbose_name="Идентификатор сообщения",
        max_length=255,
        db_index=True,
    )

    message_created_at = models.DateTimeField(
        verbose_name="Когда создано сообщение",
    )

    text = models.TextField(
        verbose_name="Текст сообщения",
    )

    sent_report = models.BooleanField(
        verbose_name="Отчет был отправлен",
        default=False,
    )

    class Meta:
        verbose_name = "Amo-задача"
        verbose_name_plural = "Amo-задачи"

        unique_together = ["account", "chat_id", "message_id"]

    def save(self, **kwargs):
        self.object_id = amo_chatbottasks.get_object_id(
            domain=self.account.domain,
            chat_id=self.chat_id,
        )
        super().save()
