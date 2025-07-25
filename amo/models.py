from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet

import chat_bot.base_models
import transcriptions.models
from amo.utils import amo_chatbottasks
from amo.utils import amo_webhooks
from chatbottasks import chatbottasks
from prompts import prompts
from utils import miscellaneous
from utils.logging import TraceLogger


class AmoAccount(models.Model):
    amo_id = models.BigIntegerField(
        verbose_name="Идентификатор в системе amo",
        primary_key=True,
    )

    telegram_id = models.CharField(
        verbose_name="ID телеграм-чата",
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


class AmoPipelineStatus(models.Model):
    account = models.ForeignKey(
        verbose_name="Amo-аккаунт",
        to=AmoAccount,
        on_delete=models.CASCADE,
    )

    account_name = models.CharField(
        verbose_name="Название Amo-аккаунта",
        max_length=255,
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

    class Meta:
        verbose_name = "Этап Amo-воронки"
        verbose_name_plural = "Этапы Amo-воронок"

        unique_together = ["account", "pipeline_id", "amo_id"]

    def save(self, *args, **kwargs) -> None:
        self.account_name = self.account.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pipeline_name} -> {self.name} ({self.account_name})"


class AmoChatBot(chat_bot.base_models.AIChatBotBase):
    account = models.ForeignKey(
        verbose_name="Amo-аккаунт",
        to=AmoAccount,
        on_delete=models.CASCADE,
    )

    change_status_only_when_qualification = models.BooleanField(
        verbose_name="Менять статус только при достижении квалификации",
        default=True,
    )

    new_status_when_qualification = models.ForeignKey(
        verbose_name="Этап воронки при достижении квалификации",
        to=AmoPipelineStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    message_when_qualification = models.TextField(
        verbose_name="Сообщение при достижении квалификации",
        blank=True,
    )

    message_when_note_received = models.TextField(
        verbose_name="Сообщение при получении заявки с сайта",
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

    duplicate_instructions = models.TextField(
        verbose_name="Важные команды еще раз",
        blank=True,
    )

    pipeline_status_update_rules = models.TextField(
        verbose_name="Правила обновления этапа воронки",
        blank=True,
    )

    message_prefix = models.TextField(
        verbose_name="Префикс сгенерированного сообщения",
        blank=True,
    )

    message_postfix = models.TextField(
        verbose_name="Постфикс сгенерированного сообщения",
        default="...",
        blank=True,
    )

    work_on_mon = models.BooleanField("Работает в пн", default=True)
    work_on_tue = models.BooleanField("Работает во вт", default=True)
    work_on_wed = models.BooleanField("Работает в ср", default=True)
    work_on_thu = models.BooleanField("Работает в чт", default=True)
    work_on_fri = models.BooleanField("Работает в пт", default=True)
    work_on_sat = models.BooleanField("Работает в сб", default=True)
    work_on_sun = models.BooleanField("Работает в вскр", default=True)

    class Meta:
        verbose_name = "Amo чат-бот"
        verbose_name_plural = "Amo чат-боты"

    @classmethod
    def get_available_chatbots(cls):
        day_of_week = miscellaneous.datetime_now_with_tz(utc_offset_hours=3).weekday()

        if day_of_week == 0:
            field = "work_on_mon"
        elif day_of_week == 1:
            field = "work_on_tue"
        elif day_of_week == 2:
            field = "work_on_wed"
        elif day_of_week == 3:
            field = "work_on_thu"
        elif day_of_week == 4:
            field = "work_on_fri"
        elif day_of_week == 5:
            field = "work_on_sat"
        elif day_of_week == 6:
            field = "work_on_sun"
        else:
            raise Exception("Unreacheble")

        kwargs = {field: True}

        return super().get_available_chatbots().filter(**kwargs)

    def get_default_name(self) -> str:
        return self.account.name

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)

        active_chatbots_exists = AmoChatBot.objects.filter(
            account=self.account,
            is_active=True,
        ).exists()

        if active_chatbots_exists:
            amo_webhooks.subscribe_for_webhooks(self.account, tlogger=TraceLogger())

        if not active_chatbots_exists:
            try:
                amo_webhooks.unsubscribe_from_webhooks(self.account, tlogger=TraceLogger())
            except:
                pass

    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:
        res = super().delete(*args, **kwargs)

        active_chatbots_exists = AmoChatBot.objects.filter(
            account=self.account,
            is_active=True,
        ).exists()

        if not active_chatbots_exists:
            try:
                amo_webhooks.unsubscribe_from_webhooks(self.account, tlogger=TraceLogger())
            except:
                pass

        return res

    def __str__(self):
        return f"{self.name} ({self.pk})"


class AmoPipelineStatusChatbotLink(models.Model):
    chatbot = models.ForeignKey(
        verbose_name="Чат-бот",
        to=AmoChatBot,
        on_delete=models.CASCADE,
    )

    status = models.OneToOneField(
        verbose_name="Этап воронки",
        to=AmoPipelineStatus,
        on_delete=models.CASCADE,
    )

    check_qualification = models.BooleanField(
        verbose_name="Проверять квалификацию",
        default=False,
    )

    class Meta:
        verbose_name = "Связь бот-воронка"
        verbose_name_plural = "Связи бот-воронка"


class AmoOrigin(models.Model):
    account = models.ForeignKey(
        verbose_name="Amo-аккаунт",
        to=AmoAccount,
        on_delete=models.CASCADE,
    )

    amo_id = models.CharField(
        verbose_name="Идентификатор в системе Amo",
        max_length=64,
        primary_key=True,
    )

    name = models.CharField(
        verbose_name="Название",
        max_length=255,
    )

    origin_title = models.CharField(
        verbose_name="Заголовок источника",
        max_length=255,
        blank=True,
    )

    source_name = models.CharField(
        verbose_name="Название источника",
        max_length=255,
        blank=True,
    )

    origin = models.CharField(
        verbose_name="Источник",
        max_length=255,
        db_index=True,
    )

    class Meta:
        verbose_name = "Amo-источник"
        verbose_name_plural = "Amo-источники"

    def __str__(self):
        return " | ".join([
            self.name or "-",
            self.origin_title or "-",
            self.source_name or "-",
            self.origin or "-",
        ])


class AmoChatbotOriginLink(models.Model):
    chatbot = models.ForeignKey(
        verbose_name="Чат-бот",
        to=AmoChatBot,
        on_delete=models.CASCADE,
    )

    origin = models.ForeignKey(
        verbose_name="Источник",
        to=AmoOrigin,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Связь бот-источник"
        verbose_name_plural = "Связи бот-источник"

        unique_together = ["chatbot", "origin"]


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
        verbose_name="К чему относится",
        choices=AmoEntity.choices,
    )

    description = models.TextField(
        verbose_name="Описание для промпта",
    )

    required_for_qualification = models.BooleanField(
        verbose_name="Нужно для квалификации",
        default=False,
    )

    isolated_check = models.BooleanField(
        verbose_name="Проверять отдельно",
        default=False,
    )

    class Meta:
        verbose_name = "Заполняемое поле"
        verbose_name_plural = "Заполняемые поля"


class AmoChatCreateConfig(models.Model):
    account = models.ForeignKey(
        verbose_name="Amo-аккаунт",
        to=AmoAccount,
        on_delete=models.CASCADE,
    )

    source = models.ForeignKey(
        verbose_name="Источник",
        to=AmoOrigin,
        on_delete=models.CASCADE,
    )

    phone_number_field = models.CharField(
        verbose_name="Поле с номером телефона",
        max_length=255,
    )

    channel_id = models.CharField(
        verbose_name="Идентификатор канала",
        max_length=63,
        help_text=(
            "При инициации общения с пользователем, "
            "AmoCRM делает запрос '/ajax/v1/chats/create', "
            "создающий чат, и передает туда scope_id, "
            "состоящий из <channel_id>_<amojo_id>"
        ),
    )

    class Meta:
        verbose_name = "Конфиг для создания чата"
        verbose_name_plural = "Конфиги для создания чата"


class AmoTalkLeadLink(models.Model):
    account = models.ForeignKey(
        verbose_name="Amo-аккаунт",
        to=AmoAccount,
        on_delete=models.CASCADE,
    )

    talk_id = models.BigIntegerField(
        verbose_name="Идентификатор разговора в системе амо",
        db_index=True,
    )

    lead_id = models.BigIntegerField(
        verbose_name="Идентификатор сделки в системе амо",
        db_index=True,
    )

    class Meta:
        verbose_name = "Связь разговор-сделка"
        verbose_name = "Связи разговор-сделка"

        unique_together = ["talk_id", "lead_id"]


class AmoChatBotTask(chat_bot.base_models.AIResultContainer, chatbottasks.Task):
    class MessageType(models.TextChoices):
        TEXT = "text"
        VOICE = "voice"
        PICTURE = "picture"

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

    # В рамках одной сделки может быть много разговоров
    talk_id = models.IntegerField(
        verbose_name="Идентификатор разговора",
        db_index=True,
        null=True,
        blank=True,
    )

    message_id = models.CharField(
        verbose_name="Идентификатор сообщения",
        max_length=255,
        db_index=True,
    )

    message_created_at = models.DateTimeField(
        verbose_name="Когда создано сообщение",
    )

    message_type = models.CharField(
        verbose_name="Тип сообщения",
        choices=MessageType.choices,
        default=MessageType.TEXT.value,
    )

    text = models.TextField(
        verbose_name="Текст сообщения",
        blank=True,
    )

    file_link = models.TextField(
        verbose_name="Прикрепленный файл",
        blank=True,
    )

    sent_report = models.BooleanField(
        verbose_name="Отчет был отправлен",
        default=False,
    )

    class Meta:
        verbose_name = "Amo-задача"
        verbose_name_plural = "Amo-задачи"

        unique_together = ["account", "chat_id", "message_id"]

    def cancel_if_not_newest(self, *, tlogger: TraceLogger) -> bool:
        """ Cancel task if newer tasks exist. Return True if canceled """

        if self.get_newer_tasks().exists():
            tlogger.info("Newer tasks found")
            self.cancel(tlogger=tlogger)
            return True

        return False

    def get_newer_tasks(self) -> QuerySet:
        return AmoChatBotTask.objects.filter(
            message_created_at__gt=self.message_created_at,
            object_id=amo_chatbottasks.get_object_id(
                domain=self.account.domain,
                chat_id=self.chat_id,
            ),
        )

    def save(self, **kwargs):
        self.object_id = amo_chatbottasks.get_object_id(
            domain=self.account.domain,
            chat_id=self.chat_id,
        )
        super().save()


class AmoTranscription(models.Model):
    account = models.ForeignKey(
        verbose_name="Амо-аккаунт",
        to=AmoAccount,
        on_delete=models.CASCADE,
    )

    chat_id = models.CharField(
        verbose_name="Идентификатор чата",
        max_length=255,
        db_index=True,
    )

    message_id = models.CharField(
        verbose_name="Идентификатор сообщения",
        max_length=255,
        db_index=True,
    )

    transcription = models.ForeignKey(
        verbose_name="Транскрипция",
        to=transcriptions.models.Transcription,
        on_delete=models.CASCADE,
    )


class AmoPrompt(prompts.PromptBase):
    chatbot = models.ForeignKey(
        verbose_name="Чат-бот",
        to=AmoChatBot,
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = "Amo-промпт"
        verbose_name_plural = "Amo-промпты"
