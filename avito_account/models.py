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
        return f"{self.name}, {self.id}"


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



