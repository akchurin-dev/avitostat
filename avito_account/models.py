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
    avito_account = models.ForeignKey(AvitoAccount, on_delete=models.CASCADE, null=True)

    address = models.CharField(max_length=255)
    category = models.JSONField()
    price = models.IntegerField()
    status = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    url = models.CharField(max_length=255)

    def __str__(self):
        return self.id


class ServiceType(models.Model):
    service_name = models.CharField(max_length=255, null=True)
    service_type = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.service_name


class Operation(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    updated_at = models.DateTimeField()


