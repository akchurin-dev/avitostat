from django.db import models
import requests
from django.shortcuts import redirect

from avito_account.models.models import AvitoAccount, BaseModel


class AmocrmAccount(models.Model):
    avito_account = models.ForeignKey(AvitoAccount, on_delete=models.CASCADE)
    integration_id = models.IntegerField(primary_key=True, unique=True)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Амосрм аккаунт"
        verbose_name_plural = "Амосрм аккаунты"

    # def save(self, *args, **kwargs):
    #     if self.integration_id is not None:
    #         super().save(*args, **kwargs)
    #         return redirect(f"https://www.amocrm.ru/oauth?client_id=5cc2f970-fe3d-47a0-9b38-86d531fa92ff&state={123}"
    #         )

