from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.views import View

from ai_messaging.api import subscribe_messages
from avito_account.models.models import AvitoAccount


# Create your views here.
class WebhookInboxView(View):
    async def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok"}, status=200)


class SubscribeTestView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)
        await subscribe_messages(avito_account)  #RAUF
        return JsonResponse({"status": "ok"}, status=200)
