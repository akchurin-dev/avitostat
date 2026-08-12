from django.core.validators import MinValueValidator
from django.db.models import F
from django.db.models import Q
from django.db import models

from utils import miscellaneous


class AIChatBotBase(models.Model):
    _default_name = "Безымянный ИИ"

    name = models.CharField(
        verbose_name="Название",
        max_length=255,
        db_index=True,
        default=_default_name,
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

    def get_default_name(self) -> str:
        return self._default_name

    def save(self, *args, **kwargs):
        if not self.name or self.name == self._default_name:
            self.name = self.get_default_name()

        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.pk})"


class AIResultContainer(models.Model):
    answer_text = models.TextField(verbose_name="Текст ответа", blank=True, null=True)
    answered_at = models.DateTimeField(verbose_name="Когда отвечено", null=True, default=None)
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
