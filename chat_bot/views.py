from asgiref.sync import sync_to_async
from django.views.decorators.csrf import csrf_exempt
from avito_account.models.models import AvitoAccount

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
import json
from pprint import pprint

from chat_bot.api.subscriptions import subscribe_to_messages, stop_subscribe_to_messages, check_subscriptions
from chat_bot.tasks import process_webhook_task


@method_decorator(csrf_exempt, name='dispatch')
class WebhookInboxView(View):
    async def post(self, request, *args, **kwargs):
        decoded_string = request.body.decode('utf-8')
        data = json.loads(decoded_string)
        pprint(data)

        user_id = data.get("payload").get("value").get("user_id")

        # Немедленно отправляем статус 200
        response = JsonResponse({"status": "ok"}, status=200)

        # Запускаем задачу Celery
        process_webhook_task.delay(user_id, data)  # Используем delay для запуска задачи

        return response


class SubscribeView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)  #Rauf
        # avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=184762136)  #Amanatauto
        await subscribe_to_messages(avito_account)
        return JsonResponse({"status": "ok"}, status=200)


class StopSubscribeView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)  #Rauf
        await avito_account.update_refresh_token_async()
        # avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=184762136)  #Amanatauto
        await stop_subscribe_to_messages(avito_account)
        return JsonResponse({"status": "ok"}, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class CheckSubscribtionsView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)  # Rauf
        await check_subscriptions(avito_account)
        return JsonResponse({"status": "ok"}, status=200)
