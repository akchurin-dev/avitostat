from asgiref.sync import async_to_sync
from django.db import models
from django.db.models import F
from django.db.models import Q
from django.core.validators import MinValueValidator

from avito_account.utils import avito_webhooks
from avito_account.models.models import AvitoAccount
from base.settings import ENVIRONMENT
from chat_bot.api.subscriptions import asubscribe_to_messages, astop_subscribe_to_messages
from chat_bot.utils import companies_branches
from prompts import prompts
from utils import miscellaneous


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


class AIChatBotBase(models.Model):
    name = models.CharField(
        verbose_name="Название",
        max_length=255,
        db_index=True,
        default="Безымянный ИИ",
    )

    is_active = models.BooleanField(default=False, verbose_name="Активирован")

    waiting_seconds = models.PositiveSmallIntegerField(
        verbose_name="Ожидание ответа от менеджера (секунды)",
        default=30,
        validators=[MinValueValidator(0)],
    )
    shutdown_after_manager = models.BooleanField(default=False, verbose_name="Выключаться после менеджера")

    work_time_from = models.TimeField("Начало работы МСК (Пн-Вс)")
    work_time_to = models.TimeField("Окончание работы МСК (Пн-Вс)")

    class Meta:
        abstract = True

    @classmethod
    def get_available_chatbots(cls):
        msk_time_now = miscellaneous.datetime_now_with_tz(utc_offset_hours=3).time()

        return cls.objects.filter(
            Q(
                work_time_from__lte=msk_time_now,
                work_time_to__gte=msk_time_now,
            ) | Q(
                Q(work_time_from__lte=msk_time_now) | Q(work_time_to__gte=msk_time_now),
                work_time_from__gte=F("work_time_to"),
            ),
            is_active=True,
        )

    def __str__(self):
        return f"{self.name} ({self.pk})"


class AiChatBot(AIChatBotBase):
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


class ClientContactsContainer(models.Model):
    # Contact fields
    address = models.TextField(blank=True, null=True, default=None, verbose_name="Адрес клиента")
    mobile = models.TextField(blank=True, null=True, default=None, verbose_name="Мобильный номер")
    whatsapp = models.TextField(blank=True, null=True, default=None, verbose_name="Вацап")
    telegram = models.TextField(blank=True, null=True, default=None, verbose_name="Телеграм")
    email = models.TextField(blank=True, null=True, default=None, verbose_name="Емайл")

    class Meta:
        abstract = True

    @classmethod
    def save_contacts(
        cls,
        pk,
        address: str | None,
        mobile: str | None,
        whatsapp: str | None,
        telegram: str | None,
        email: str | None,
    ) -> None:

        contact = cls.objects.get(pk=pk)

        if address:
            contact.address = address

        if mobile:
            contact.mobile = mobile

        if whatsapp:
            contact.whatsapp = whatsapp

        if telegram:
            contact.telegram = telegram

        if email:
            contact.email = email

        contact.save()


class AIResultContainer(models.Model):
    answer_text = models.TextField(verbose_name="Текст ответа", blank=True, null=True)
    tokens_completion = models.IntegerField(default=0, verbose_name="Токены на вычисления")
    tokens_prompt = models.IntegerField(default=0, verbose_name="Токены на контекст")

    class Meta:
        abstract = True

    @classmethod
    def save_ai_result(cls, pk, answer_text: str, tokens_completion: int, tokens_prompt: int) -> None:
        cls.objects.filter(pk=pk).update(
            answer_text=answer_text,
            tokens_completion=tokens_completion,
            tokens_prompt=tokens_prompt,
        )


class ChatBotTask(AIResultContainer, ClientContactsContainer):
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
