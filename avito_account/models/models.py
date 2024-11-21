import logging
import httpx
import pytz
import sentry_sdk
from asgiref.sync import sync_to_async
from django.db import models
from django.contrib.auth.models import User
import requests
from base import settings
from base.exceptions import HTTPException
import datetime

logger = logging.getLogger(__name__)

client_id = settings.AVITO_CLIENT_ID
client_secret = settings.AVITO_CLIENT_SECRET
MOSCOW_TZ = pytz.timezone('Europe/Moscow')


def moscow_time(hour, minute):
    dt = datetime.datetime.now(MOSCOW_TZ).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return dt.time()


class BaseModel(models.Model):
    created_by = models.ForeignKey(
        verbose_name="Кем создано",
        to=User,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_created_by",
    )
    created_at = models.DateTimeField(
        verbose_name="Когда создано",
        auto_now_add=True,
    )

    @classmethod
    def filter_queryset_by_company(
            cls, queryset: models.QuerySet, user: "User"
    ) -> models.QuerySet:
        if user.is_superuser:
            return cls.objects.all()
        if hasattr(cls, "pbx_account"):
            return cls.objects.filter(pbx_account__created_by=user)
        return cls.objects.filter(created_by=user)

    class Meta:
        abstract = True


class AnalyticSchema(BaseModel):
    name = models.CharField(max_length=32, verbose_name="Название схемы")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Схема аналитики"
        verbose_name_plural = "Схемы аналитики"


class Criterion(models.Model):  # Не BaseModel тк привязываемся к схеме и этого достаточно
    schema = models.ForeignKey(AnalyticSchema, on_delete=models.CASCADE, related_name="criteria",
                               verbose_name="Схема аналитики")
    name = models.CharField(verbose_name="Название")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Критерий оценки"
        verbose_name_plural = "Критерии оценки"


class AvitoAccount(BaseModel):
    name = models.CharField(max_length=255, null=True, verbose_name="Название аккаунта")
    telegram_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="Телеграм ID")
    phone = models.CharField(max_length=255, null=True, verbose_name="Номер телефона")
    profile_url = models.CharField(max_length=255, null=True, verbose_name="Ссылка на профиль")
    access_token = models.CharField(max_length=255, null=True, verbose_name="Токен доступа")
    refresh_token = models.CharField(max_length=255, null=True, verbose_name="Токен обновления")

    analytic_schema = models.ForeignKey(AnalyticSchema, on_delete=models.SET_NULL, null=True, blank=True,
                                        verbose_name="Схема аналитики")
    balance_keeper = models.BooleanField(default=True, verbose_name="Уведомления о заканчивающемся балансе")

    def update_refresh_token(self):
        url = 'https://api.avito.ru/token/'
        data = {
            'grant_type': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': self.refresh_token
        }

        response = requests.post(url, data=data)
        response_data = response.json()

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        else:
            self.access_token = response_data['access_token']
            self.refresh_token = response_data['refresh_token']
            self.save()
            return True

    async def update_refresh_token_async(self):
        url = 'https://api.avito.ru/token/'
        data = {
            'grant_type': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': self.refresh_token
        }

        for attempt in range(3):  # Not more 3 tries
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, data=data, timeout=300)
                    if response.status_code == 200:
                        response_data = response.json()
                        self.access_token = response_data['access_token']
                        self.refresh_token = response_data['refresh_token']
                        await sync_to_async(self.save)()
                        return True
            except HTTPException as e:
                if attempt == 2:
                    sentry_sdk.capture_exception(e)

    def __str__(self):
        return f"{self.name}, {self.telegram_id}"

    class Meta:
        verbose_name = "Авито аккаунт"
        verbose_name_plural = "Авито аккаунты"


class WorkSchedule(models.Model):  # Не BaseModel тк привязываемся к AvitoAccount и этого достаточно
    avito_account = models.OneToOneField(AvitoAccount, on_delete=models.CASCADE, related_name="work_schedules",
                                         null=True,
                                         blank=True
                                         , verbose_name="Авито аккаунт")

    # Рабочие дни с понедельника по пятницу
    # TODO try to delete moscow_time - как будто не будет никакой разницы
    weekday_start = models.TimeField("Начало работы (Пн-Пт)", default=moscow_time(10, 0))
    weekday_end = models.TimeField("Окончание работы (Пн-Пт)", default=moscow_time(18, 0))

    # Суббота
    saturday_is_day_off = models.BooleanField("Суббота - выходной?", default=True)
    saturday_start = models.TimeField("Суббота - начало работы", default=moscow_time(10, 0))
    saturday_end = models.TimeField("Суббота - окончание работы", default=moscow_time(16, 0))

    # Воскресенье
    sunday_is_day_off = models.BooleanField("Воскресенье - выходной?", default=True)
    sunday_start = models.TimeField("Воскресенье - начало работы", default=moscow_time(10, 0))
    sunday_end = models.TimeField("Воскресенье - окончание работы", default=moscow_time(16, 0))

    def __str__(self):
        if self.avito_account:
            return f"Рабочий график для {self.avito_account.name} id-{self.id}"
        else:
            return f"Рабочий график по умолчанию id-{self.id}"

    class Meta:
        verbose_name = "Рабочий график (время Московское)"
        verbose_name_plural = "Рабочие графики"
