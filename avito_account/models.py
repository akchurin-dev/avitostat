import httpx
import sentry_sdk
from asgiref.sync import sync_to_async
from django.db import models
from django.contrib.auth.models import User
import os
import requests
from dotenv import load_dotenv
from exceptions import HTTPException

load_dotenv()
client_id = os.getenv('AVITO_CLIENT_ID')
client_secret = os.getenv('AVITO_CLIENT_SECRET')


class AvitoAccount(models.Model):
    company = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, null=True)
    telegram_id = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=255, null=True)
    profile_url = models.CharField(max_length=255, null=True)
    access_token = models.CharField(max_length=255, null=True)
    refresh_token = models.CharField(max_length=255, null=True)

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


class BaseModel(models.Model):
    created_by = models.ForeignKey(
        verbose_name="Created by",
        null=True,
        to=User,
        on_delete=models.SET_NULL,
        default=None,
        related_name="%(app_label)s_%(class)s_created_by",
        editable=False,
    )
    created_at = models.DateTimeField(
        verbose_name="Created At",
        auto_now_add=True,
        editable=False
    )

    @classmethod
    def filter_queryset_by_company(
            cls, queryset: models.QuerySet, user: "User"
    ) -> models.QuerySet:
        if user.is_superuser:
            return cls.objects.all()
        # if hasattr(cls, "pbx_account"):
        #     return cls.objects.filter(pbx_account__created_by__company=user.company)
        # if hasattr(cls, "phone"):
        #     return cls.objects.filter(phone__created_by__company=user.company)
        # if hasattr(cls, "call"):
        #     return cls.objects.filter(call__phone__created_by__company=user.company)
        return cls.objects.filter(created_by__company=user.company)

    class Meta:
        abstract = True


class Condition(BaseModel):
    name = models.CharField(
        max_length=64,
        verbose_name="Condition",
        unique=True,
        help_text="Продолжите фразу: при условии что ...",
    )

    class Meta:
        db_table = "conditions"
        verbose_name = "Condition"
        verbose_name_plural = "Conditions"

    def __str__(self):
        return self.name


class ConditionResult(BaseModel):
    call = models.ForeignKey(
        Call, on_delete=models.CASCADE, related_name="condition_results"
    )
    condition = models.ForeignKey(
        Condition, on_delete=models.PROTECT, related_name="condition_results"
    )
    is_compliant = models.BooleanField(default=False, verbose_name=_("Compliant"))

    class Meta:
        db_table = "condition_results"
        verbose_name = "Condition Result"
        verbose_name_plural = "Condition Results"


class AnalyticSchema(BaseModel):
    name = models.CharField(max_length=32, verbose_name="Schemas Name")

    class Meta:
        db_table = "analytic_schemas"
        verbose_name = "Analytic Schema"
        verbose_name_plural = "Analytic Schemas"

    def __str__(self):
        return self.name


class Criterion(BaseModel):
    schema = models.ForeignKey(
        AnalyticSchema, on_delete=models.CASCADE, related_name="criteria"
    )
    # TODO change to CharField
    name = models.TextField(verbose_name="Name")
    condition_fk = models.ForeignKey(
        Condition,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="criteria",
    )

    class Meta:
        db_table = "criteria"
        verbose_name = "Criterion"
        verbose_name_plural = "Criteria"

    def __str__(self):
        return self.name


class CriterionResult(BaseModel):
    call = models.ForeignKey(
        Call, on_delete=models.CASCADE, related_name="criterion_results"
    )
    criterion = models.ForeignKey(
        Criterion, on_delete=models.CASCADE, related_name="criterion_results"
    )
    is_positive = models.BooleanField(default=False, verbose_name=_("Positive Result"))
    description = models.TextField(
        verbose_name="Description Of Result", null=True, blank=True
    )
    meets_condition = models.BooleanField(
        default=True, verbose_name="Meets Condition"
    )

    class Meta:
        db_table = "criterion_results"
        verbose_name = "Criterion result"
        verbose_name_plural = "Criteria results"

# class Item(models.Model):
#     avito_account = models.ForeignKey(AvitoAccount, on_delete=models.CASCADE)
#
#     address = models.CharField(max_length=255)
#     category = models.JSONField()
#     price = models.IntegerField(null=True)
#     status = models.CharField(max_length=255)
#     title = models.CharField(max_length=255)
#     url = models.CharField(max_length=255)
#
#     def __str__(self):
#         return f"{self.title, self.id}"
