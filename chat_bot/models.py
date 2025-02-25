from asgiref.sync import async_to_sync
from django.db import models
from django.contrib.auth.models import User
from avito_account.models.models import AvitoAccount, moscow_time
from base.settings import ENVIRONMENT
from chat_bot.api.subscriptions import subscribe_to_messages, stop_subscribe_to_messages
from django.core.validators import MinValueValidator, MaxValueValidator


class AIChatBotBase(models.Model):
    is_active = models.BooleanField(default=False, verbose_name="Активирован")
    total_info = models.TextField(verbose_name="Общая информация")
    rules = models.TextField(verbose_name="Правила при общении")
    checkpoints = models.TextField(verbose_name="Шаги при общении")
    target_action = models.TextField(verbose_name="Целевое действие",
                                     default="Взять номер телефона клиента для связи")

    work_time_from = models.TimeField("Начало работы МСК (Пн-Вс)")
    work_time_to = models.TimeField("Окончание работы МСК (Пн-Вс)")

    class Meta:
        abstract = True


class AiChatBot(AIChatBotBase):
    avito_account = models.OneToOneField(
        AvitoAccount,
        on_delete=models.CASCADE,
        related_name='ai_chat_bots',
        verbose_name="ИИ чат бот"
    )

    waiting_minutes = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(60)],
        verbose_name="Ожидание ответа от менеджера(минуты)",
        help_text="Укажите количество минут от 1 до 120"
    )
    shutdown_after_manager = models.BooleanField(default=False, verbose_name="Выключаться после менеджера")

    statistics_daily_report = models.BooleanField(default=True, verbose_name="Ежедневная статистика")
    histories_closed = models.BooleanField(default=False, verbose_name="История дожатых клиентов")
    histories_open = models.BooleanField(default=False, verbose_name="История НЕдожатых клиентов")

    class Meta:
        verbose_name = "ИИ чат бот"
        verbose_name_plural = "ИИ чат боты"

    def save(self, *args, **kwargs):
        previous = AiChatBot.objects.filter(pk=self.pk).last()
        # Сначала сохраняем объект
        super().save(*args, **kwargs)

        if ENVIRONMENT == "DEVELOPMENT":
            async_to_sync(self.avito_account.update_refresh_token_async)()

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


class ChatBotTask(models.Model):
    # Core fields
    avito_account = models.ForeignKey(AvitoAccount, on_delete=models.CASCADE)
    is_incoming = models.BooleanField(default=True, verbose_name="Входящее сообщение")
    chat_id = models.CharField()
    message_id = models.CharField(primary_key=True, unique=True)
    text = models.TextField(verbose_name="Текст сообщения")

    # AI fields
    answer_text = models.TextField(verbose_name="Текст ответа", blank=True, null=True)
    tokens_completion = models.IntegerField(default=0, verbose_name="Токены на вычисления")
    tokens_prompt = models.IntegerField(default=0, verbose_name="Токены на контекст")

    # Contact fields
    address = models.TextField(blank=True, null=True, default=None, verbose_name="Адрес клиента")
    mobile = models.TextField(blank=True, null=True, default=None, verbose_name="Мобильный номер")
    whatsapp = models.TextField(blank=True, null=True, default=None, verbose_name="Вацап")
    telegram = models.TextField(blank=True, null=True, default=None, verbose_name="Телеграм")
    email = models.TextField(blank=True, null=True, default=None, verbose_name="Емайл")

    # Service fields
    summary_sanded = models.BooleanField(default=False, verbose_name="Сводка была отправлена")
    chat_shutdown_by_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ответ чат бота"
        verbose_name_plural = "Ответы чат бота"

    def __str__(self):
        return f"{self.message_id}"
