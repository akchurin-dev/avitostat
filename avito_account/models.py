import httpx
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

    async def update_refresh_token_async(self, max_retries: int = 3):
        url = 'https://api.avito.ru/token/'
        data = {
            'grant_type': 'refresh_token',
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': self.refresh_token
        }

        retries = 0

        async with httpx.AsyncClient() as client:
            while retries <= max_retries:
                response = await client.post(url, data=data, timeout=300)
                if response.status_code == 200:
                    response_data = response.json()
                    self.access_token = response_data['access_token']
                    self.refresh_token = response_data['refresh_token']
                    await sync_to_async(self.save)()
                    return True
                else:
                    retries += 1
                    if retries > max_retries:
                        raise HTTPException(status_code=response.status_code, detail=response.text)

    def __str__(self):
        return f"{self.name}, {self.telegram_id}"


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
