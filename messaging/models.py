from django.db import models

from avito_account.models.models import AvitoAccount


class ReportMonth(models.Model):
    month = models.IntegerField()
    account = models.ForeignKey(AvitoAccount, on_delete=models.CASCADE)
    data = models.JSONField()
