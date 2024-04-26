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
