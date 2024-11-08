from asgiref.sync import sync_to_async, async_to_sync
from celery.result import AsyncResult
from django.views.decorators.csrf import csrf_exempt
from avito_account.models.models import AvitoAccount
from chat_bot.models import AiChatBot
from chat_bot.tasks import delayed_task
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
import json
from pprint import pprint
from base.celery import celery_app, logger

from chat_bot.api.subscriptions import subscribe_to_messages, stop_subscribe_to_messages, check_subscriptions


@method_decorator(csrf_exempt, name='dispatch')
class WebhookInboxView(View):
    async def post(self, request, *args, **kwargs):
        decoded_string = request.body.decode('utf-8')
        data = json.loads(decoded_string)
        user_id = data.get("payload").get("value").get("user_id")
        # Немедленно отправляем статус 200, иначе сервер повторно отправит запрос
        response = JsonResponse({"status": "ok"}, status=200)

        avito_account = await AvitoAccount.objects.aget(id=user_id)
        chat_bot = await AiChatBot.objects.aget(avito_account=avito_account)
        await avito_account.update_refresh_token_async()

        if data.get("payload").get("type") == "message":
            chat_id = data.get("payload").get("value").get("chat_id")
            author_id = data.get("payload").get("value").get("author_id")
            content = data.get("payload").get("value").get("content")

            if author_id != user_id and chat_bot.is_active:
                task_id = f"task_ai_answer_for_chat_id_{chat_id}"
                # Проверяем, существует ли задача с таким task_id и активна ли она
                existing_task = AsyncResult(task_id)
                if existing_task and existing_task.state in ["PENDING", "STARTED"]:
                    # Если задача активна или ожидает выполнения, отменяем её
                    existing_task.revoke(terminate=True)
                    logger.info(f"Task {task_id} revoked before creating the new task.")
                # Создаем новую задачу с тем же task_id
                delayed_task.apply_async(
                    (avito_account.id, user_id, chat_id, chat_bot.id, content),
                    countdown=240,
                    task_id=task_id
                )

        return response


class SubscribeView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)  #Rauf
        await subscribe_to_messages(avito_account)
        return JsonResponse({"status": "ok"}, status=200)


class StopSubscribeView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)  #Rauf
        await avito_account.update_refresh_token_async()
        await stop_subscribe_to_messages(avito_account)
        return JsonResponse({"status": "ok"}, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class CheckSubscribtionsView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)  # Rauf
        await check_subscriptions(avito_account)
        return JsonResponse({"status": "ok"}, status=200)
