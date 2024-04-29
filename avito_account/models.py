from django.db import models
from django.contrib.auth.models import User


class AvitoAccount(models.Model):
    company = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=255, null=True)
    phone = models.CharField(max_length=255, null=True)
    profile_url = models.CharField(max_length=255, null=True)
    access_token = models.CharField(max_length=255, null=True)
    refresh_token = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.name


class Item(models.Model):
    avito_account = models.ForeignKey(AvitoAccount, on_delete=models.CASCADE)

    address = models.CharField(max_length=255)
    category = models.JSONField()
    price = models.IntegerField(null=True)
    status = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    url = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.title, self.id}"


class ServiceType(models.Model):
    service_name = models.CharField(max_length=255, null=True)
    service_type = models.CharField(max_length=255, null=True)
    service_id = models.IntegerField(null=True)

    def __str__(self):
        return self.service_name


class Operation(models.Model):
    amount_bonus = models.IntegerField()
    amount_rub = models.IntegerField()
    amount_total = models.IntegerField()
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=255, null=True)
    type = models.CharField(max_length=255, null=True)
    service = models.ForeignKey(ServiceType, on_delete=models.CASCADE)
    updated_at = models.DateTimeField()

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ['updated_at', 'name']