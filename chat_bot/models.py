from django.db import models

import chat_bot.base_models
from avito_account.utils import avito_webhooks
from avito_account.models.models import AvitoAccount
from chat_bot.utils import companies_branches
from prompts import prompts


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


class AiChatBot(chat_bot.base_models.AIChatBotBase):
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


class ChatBotTask(chat_bot.base_models.AIResultContainer, chat_bot.base_models.ClientContactsContainer):
    # Core fields
    avito_account = models.ForeignKey(AvitoAccount, on_delete=models.CASCADE)
    company_branch = models.ForeignKey(CompanyBranch, on_delete=models.SET_NULL, null=True, blank=True)
    is_incoming = models.BooleanField(default=True, verbose_name="Входящее сообщение")
    chat_id = models.CharField()
    message_id = models.CharField(primary_key=True, unique=True)
    text = models.TextField(verbose_name="Текст сообщения")

    # Service fields
    summary_sanded = models.BooleanField(default=False, verbose_name="Сводка была отправлена")
    chat_shutdown_by_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ответ чат бота"
        verbose_name_plural = "Ответы чат бота"

    def __str__(self):
        return f"{self.message_id}"
