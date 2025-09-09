from __future__ import annotations

import datetime
import logging
import pytz

from django.contrib.auth.models import User
from django.db import models
from django.db.models.query import QuerySet

from base import settings
from utils import httpx_helper


logger = logging.getLogger(__name__)

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
    balance_alerting = models.BooleanField(default=True, verbose_name="Уведомления о заканчивающемся балансе")

    def update_refresh_token(self):
        url = 'https://api.avito.ru/token/'

        data = {
            'grant_type': 'refresh_token',
            'client_id': settings.AVITO_CLIENT_ID,
            'client_secret': settings.AVITO_CLIENT_SECRET,
            'refresh_token': self.refresh_token
        }

        for _ in range(4):
            response = httpx_helper.request("POST", url, data=data)
            if response.is_success:
                break

        response.raise_for_status()
        response_data = response.json()

        self.access_token = response_data['access_token']
        self.refresh_token = response_data['refresh_token']

        self.save()

        return True

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
            return f"Рабочий график для {self.avito_account.name} id-{self.pk}"
        else:
            return f"Рабочий график по умолчанию id-{self.pk}"

    class Meta:
        verbose_name = "Рабочий график (время Московское)"
        verbose_name_plural = "Рабочие графики"


class AvitoItem(models.Model):
    id = models.BigIntegerField(
        verbose_name="Идентификатор в системе Авито",
        primary_key=True,
    )

    account_id: int
    account = models.ForeignKey(
        verbose_name="Авито-аккаупт",
        to=AvitoAccount,
        on_delete=models.CASCADE,
    )

    url = models.CharField(
        verbose_name="URL",
        max_length=255,
        null=True,
    )

    relative_link = models.CharField(
        verbose_name="Относительная ссылка",
        max_length=255,
        null=True,
        db_index=True,
    )

    title = models.CharField(
        verbose_name="Название",
        max_length=255,
    )

    address = models.CharField(
        verbose_name="Адрес",
        max_length=255,
    )

    price = models.IntegerField(
        verbose_name="Цена",
        null=True,
    )

    status = models.CharField(
        verbose_name="Статус",
    )

    class Meta:
        verbose_name = "Объявление"
        verbose_name_plural = "Объявления"

    def set_url(self, url: str | None) -> None:
        """ Обновляет url и relative_link """

        if url is None:
            self.url = None
            self.relative_link = None
            return

        self.url = url
        self.relative_link = AvitoItem.item_url_to_relative_link(url)

    @staticmethod
    def get_by_account(account_id: int) -> QuerySet[AvitoItem]:
        return AvitoItem.objects.filter(account_id=account_id)

    @staticmethod
    def delete_non_existing(account_id: int, existing_items_ids: list[int]) -> None:
        AvitoItem.objects.filter(account_id=account_id).exclude(id__in=existing_items_ids).delete()

    @staticmethod
    def create_instance(
        account_id: int,
        id: int,
        url: str | None,
        title: str,
        address: str,
        price: int | None,
        status: str,
    ) -> AvitoItem:

        item = AvitoItem()

        item.id = id
        item.account_id = account_id
        item.title = title
        item.address = address
        item.price = price
        item.status = status

        item.set_url(url)

        return item

    @staticmethod
    def get_by_url(url: str) -> AvitoItem | None:
        relative_link = AvitoItem.item_url_to_relative_link(url)
        return AvitoItem.objects.filter(relative_link=relative_link).select_related("account").first()

    @staticmethod
    def item_url_to_relative_link(url: str) -> str:
        """
            Transfer urls like 
            https://www.avito.ru/kazan/cars/lexus_lx_470__3313424,
            http://avito.ru/kazan/cars/lexus_lx_470__3313424 
            to /kazan/cars/lexus_lx_470__3313424
        """

        domain = "avito.ru"
        domain_pos = url.find(domain)
        assert domain_pos != -1
        return url[domain_pos + len(domain):]


class ExcludedItem(models.Model):
    avito_account = models.ForeignKey(
        'AvitoAccount',
        on_delete=models.CASCADE,
        related_name='excluded_items',
        verbose_name="Аккаунт Avito"
    )
    id = models.BigIntegerField(
        verbose_name="ID объявления",
        primary_key=True
    )

    class Meta:
        verbose_name = "Объявление исключённое"
        verbose_name_plural = "Объявления исключённые"
        unique_together = (("avito_account", "id"),)

    def __str__(self):
        return str(self.id)
