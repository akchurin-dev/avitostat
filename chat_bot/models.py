from __future__ import annotations
from enum import Enum

from django.db import models
from django.utils import timezone

import chat_bot.base_models
import transcriptions.models
from avito_account.utils import avito_webhooks
from avito_account.models.models import AvitoAccount
from chat_bot.utils import companies_branches
from prompts import prompts


class AvitoTaskStatus(str, Enum):
    CREATED = "created"
    ANSWER_GENERATION = "answer_generation"
    SUMMARY_SENDING = "summary_sending"
    CANCELED = "canceled"
    INTERRUPTED = "interrupted"
    FINISHED = "finished"


class CompanyBranch(models.Model):
    account = models.ForeignKey(
        verbose_name="Компания",
        to=AvitoAccount,
        on_delete=models.PROTECT,
    )

    location = models.CharField(
        verbose_name="Населенный пункт",
        max_length=255,
    )

    location_slug = models.CharField(
        verbose_name="Код населенного пункта",
        max_length=255,
        db_index=True,
    )

    telegram_id = models.CharField(
        verbose_name="telegram id",
        max_length=31,
    )

    class Meta:
        verbose_name = "Филиал"
        verbose_name_plural = "Филиалы"

    def save(self, *args, **kwargs):
        self.location_slug = companies_branches.get_location_code(self.location)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.location


class DialogTriggerInitiator(models.Model):
    trigger: DialogTrigger | None = models.ForeignKey(
        verbose_name="Вызывает триггер",
        to="DialogTrigger",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    delay_before_launch_trigger_sec = models.PositiveIntegerField(
        verbose_name="Запускать следующий триггер через (сек)",
        default=60 * 10,
    )

    class Meta:
        abstract = True


class AiChatBot(chat_bot.base_models.AIChatBotBase, DialogTriggerInitiator):
    account = models.OneToOneField(
        verbose_name="Авито-аккаунт",
        to=AvitoAccount,
        on_delete=models.CASCADE,
    )

    read_only = models.BooleanField(
        verbose_name="Только читает сообщения",
        default=False,
    )
    send_new_contact_report = models.BooleanField(
        verbose_name="Отправлять отчет о новом контакте",
        default=True,
    )

    statistics_daily_report = models.BooleanField(default=True, verbose_name="Ежедневная статистика")
    histories_closed = models.BooleanField(default=False, verbose_name="История дожатых клиентов")
    histories_open = models.BooleanField(default=False, verbose_name="История НЕдожатых клиентов")

    class Meta:
        verbose_name = "ИИ чат бот"
        verbose_name_plural = "ИИ чат боты"

    def get_default_name(self) -> str:
        return self.account.name or super().get_default_name()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        avito_webhooks.update_avito_webhook_subscription(self.account)

    def delete(self, using=None, keep_parents=False):
        avito_webhooks.update_avito_webhook_subscription(self.account)
        super().delete()


class AvitoPrompt(prompts.PromptBase):
    chatbot = models.ForeignKey(
        verbose_name="Чат-бот",
        to=AiChatBot,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Промпт"
        verbose_name_plural = "Промпты"

        unique_together = ["chatbot", "title"]


class ChatBotTask(
    chat_bot.base_models.AIResultContainer,
    chat_bot.base_models.ClientContactsContainer,
):
    # Core fields
    status = models.CharField(
        verbose_name="Статус",
        max_length=31,
        db_index=True,
        null=True,
        default=None,
    )
    cancel_reason = models.TextField(verbose_name="Причина отмены", blank=True, null=True, default=None)
    avito_account = models.ForeignKey(AvitoAccount, on_delete=models.CASCADE)
    company_branch = models.ForeignKey(CompanyBranch, on_delete=models.SET_NULL, null=True, blank=True)
    is_incoming = models.BooleanField(default=True, verbose_name="Входящее сообщение")
    chat_id = models.CharField()
    message_id = models.CharField(primary_key=True, unique=True)
    text = models.TextField(verbose_name="Текст сообщения")
    message_created_at = models.DateTimeField(verbose_name="Когда создано сообщение")

    # Service fields
    summary_sanded = models.BooleanField(default=False, verbose_name="Сводка была отправлена")
    chat_shutdown_by_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ответ чат бота"
        verbose_name_plural = "Ответы чат бота"

    def get_status(self) -> AvitoTaskStatus:
        return AvitoTaskStatus(self.status)

    def set_status(self, new_status: AvitoTaskStatus, save: bool = False) -> None:
        self.status = new_status.value
        if save:
            self.save()

    def cancel(self, reason: str, save: bool = False) -> None:
        self.cancel_reason = reason
        self.set_status(AvitoTaskStatus.CANCELED, save=save)

    def interrupt(self, error: Exception | str, save: bool = False) -> None:
        self.cancel_reason = str(error)
        self.set_status(AvitoTaskStatus.INTERRUPTED, save=save)

    @staticmethod
    def get_tasks_by_chat(account: AvitoAccount, chat_id: str) -> models.QuerySet[ChatBotTask]:
        return (
            ChatBotTask.objects
            .filter(
                avito_account=account,
                chat_id=chat_id,
            )
            .order_by("created_at")
        )

    def __str__(self):
        return f"{self.message_id}"


class AvitoTranscription(models.Model):
    account = models.ForeignKey(
        verbose_name="Авито-аккаунт",
        to=AvitoAccount,
        on_delete=models.CASCADE,
    )

    chat_id = models.CharField(
        verbose_name="Идентификатор чата",
        max_length=63,
        db_index=True,
    )

    message_id = models.CharField(
        verbose_name="Идентификатор сообщения",
        max_length=63,
        db_index=True,
    )

    transcription = models.ForeignKey(
        verbose_name="Транскрипция",
        to=transcriptions.models.Transcription,
        on_delete=models.CASCADE,
    )


class DialogTrigger(DialogTriggerInitiator):
    chatbot = models.ForeignKey(
        verbose_name="Чат-бот",
        to=AiChatBot,
        on_delete=models.CASCADE,
    )

    title = models.CharField(
        verbose_name="Название",
        max_length=255,
    )

    only_when_client_is_silent = models.BooleanField(
        verbose_name="Только когда клиент не отвечает",
        default=True,
    )

    additional_condition = models.TextField(
        verbose_name="Дополнительное условие",
        blank=True,
    )

    message = models.TextField(
        verbose_name="Сообщение",
    )

    class Meta:
        verbose_name = "Триггер"
        verbose_name_plural = "Триггеры"

    @staticmethod
    def get(id: int) -> DialogTrigger:
        return DialogTrigger.objects.get(pk=id)

    def __str__(self) -> str:
        return self.title


class WorkedTrigger(models.Model):
    account = models.ForeignKey(
        verbose_name="Аккаунт",
        to=AvitoAccount,
        on_delete=models.CASCADE,
    )

    trigger = models.ForeignKey(
        verbose_name="Триггер",
        to=DialogTrigger,
        on_delete=models.CASCADE,
    )

    chat_id = models.CharField(
        verbose_name="Идентификатор чата в системе Авито",
        max_length=255,
        db_index=True,
    )

    created_at = models.DateTimeField(
        verbose_name="Когда создан",
        auto_now_add=True,
    )

    @staticmethod
    def get_worked_triggers_by_chat(account: AvitoAccount, chat_id: str) -> models.QuerySet[WorkedTrigger]:
        return (
            WorkedTrigger.objects.filter(
                account=account,
                chat_id=chat_id,
            )
            .select_related("trigger")
            .order_by("created_at")
        )

    @staticmethod
    def create(chat_id: str, trigger: DialogTrigger) -> WorkedTrigger:
        return WorkedTrigger.objects.create(
            account=trigger.chatbot.account,
            chat_id=chat_id,
            trigger=trigger,
        )
