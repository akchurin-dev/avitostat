import datetime

import pytz
from asgiref.sync import sync_to_async
from celery.result import AsyncResult
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from avito_account.models.models import AvitoAccount, moscow_time
from chat_bot.models import AiChatBot, ChatBotTask
from chat_bot.tasks import delayed_func_async
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
import json
from base.celery import logger
from chat_bot.api.subscriptions import subscribe_to_messages, stop_subscribe_to_messages, check_subscriptions

moscow_tz = pytz.timezone('Europe/Moscow')


async def check_chat_bot_scheduler(chat_bot: AiChatBot):
    now = datetime.datetime.now(tz=moscow_tz)
    start = moscow_tz.localize(datetime.datetime.combine(now.date(), chat_bot.work_time_from))
    stop = moscow_tz.localize(datetime.datetime.combine(now.date(), chat_bot.work_time_to))
    return start <= now <= stop


@method_decorator(csrf_exempt, name='dispatch')
class WebhookInboxView(View):
    async def post(self, request, *args, **kwargs):
        decoded_string = request.body.decode('utf-8')
        data = json.loads(decoded_string)

        user_id = data.get("payload").get("value").get("user_id")
        avito_account = await AvitoAccount.objects.aget(id=user_id)
        chat_bot = await AiChatBot.objects.aget(avito_account=avito_account)
        await avito_account.update_refresh_token_async()

        if data.get("payload").get("type") == "message":
            message_id = data.get('payload').get('value').get('id')
            chat_id = data.get("payload").get("value").get("chat_id")
            author_id = data.get("payload").get("value").get("author_id")
            incoming_message = data.get("payload").get("value").get("content").get("text")
            time_to_work = await check_chat_bot_scheduler(chat_bot)

            if author_id != user_id and chat_bot.is_active and time_to_work:
                current_time = now().astimezone(moscow_tz)
                last_2_hours = current_time - datetime.timedelta(hours=2)

                old_tasks = await sync_to_async(list)(ChatBotTask.objects.filter(
                                                    chat_id=chat_id,
                                                    created_at__gt=last_2_hours, ))
                if old_tasks:
                    for old_task in old_tasks:
                        old_task_id = f"ai_answer_{old_task.message_id}"
                        existing_task = AsyncResult(old_task_id)
                        if existing_task and existing_task.status == "PENDING":
                            existing_task.revoke(terminate=True)
                            # logger.info(f"Task {old_task_id} revoked before launching")

                new_task, created = await ChatBotTask.objects.aget_or_create(
                    chat_id=chat_id,
                    message_id=message_id,
                    avito_account=avito_account,
                    text=incoming_message,
                )

                if created:
                    await delayed_func_async(
                        avito_account.id, user_id, chat_id, chat_bot.id, incoming_message, new_task.message_id,
                    )

        return JsonResponse({"status": "ok"}, status=200)


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
