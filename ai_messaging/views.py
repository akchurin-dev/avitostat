import json
from pprint import pprint

from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ai_messaging.api import subscribe_to_messages
from avito_account.models.models import AvitoAccount
from messaging.api import get_chats_messages


@method_decorator(csrf_exempt, name='dispatch')
class WebhookInboxView(View):
    async def post(self, request, *args, **kwargs):
        decoded_string = request.body.decode('utf-8')
        data = json.loads(decoded_string)
        avito_account = await AvitoAccount.objects.aget(id=data.get("payload").get("value").get("user_id"))
        await avito_account.update_refresh_token_async()
        if data.get("payload").get("type") == "message":
            chat_id = data.get("payload").get("value").get("chat_id")
            chat_with_messages = await get_chats_messages(avito_account, chats=[{"id": chat_id}])
            if chat_with_messages[0]['messages'][0].get("direction") == "in":
                pass

        return JsonResponse({"status": "ok"}, status=200)


class SubscribeTestView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)  #Rauf
        # avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=184762136)  #Amanatauto
        await subscribe_to_messages(avito_account)
        return JsonResponse({"status": "ok"}, status=200)

# class MySubscriptionsView(View):
#     async def post(self, request, *args, **kwargs):
