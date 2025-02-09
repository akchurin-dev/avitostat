import asyncio
import datetime

from base.settings import ENVIRONMENT
from chat_bot.tasks import BotStatisticsDailyReportClass, ChatBotSummaryReportClass, ai_answer_sender, \
    PdfReportBaseClass
import pytz
from asgiref.sync import sync_to_async, async_to_sync
from celery.result import AsyncResult
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from avito_account.models.models import AvitoAccount
from chat_bot.models import AiChatBot, ChatBotTask
from chat_bot.tasks import ai_answer_sender_task
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
import json
from chat_bot.api.subscriptions import subscribe_to_messages, stop_subscribe_to_messages, check_subscriptions
from messaging.api import MessagingAPISync

moscow_tz = pytz.timezone('Europe/Moscow')


async def check_chat_bot_scheduler(chat_bot: AiChatBot) -> bool:
    now = datetime.datetime.now(tz=moscow_tz)
    start = moscow_tz.localize(datetime.datetime.combine(now.date(), chat_bot.work_time_from))

    # Если рабочее время заканчивается на следующий день
    if chat_bot.work_time_to < chat_bot.work_time_from:
        stop = moscow_tz.localize(
            datetime.datetime.combine(now.date() + datetime.timedelta(days=1), chat_bot.work_time_to))
    else:
        stop = moscow_tz.localize(datetime.datetime.combine(now.date(), chat_bot.work_time_to))
    return start <= now <= stop


@method_decorator(csrf_exempt, name='dispatch')
class WebhookInboxView(View):
    async def revoke_old_tasks(self, chat_id: str):
        current_time = now().astimezone(moscow_tz)
        last_2_hours = current_time - datetime.timedelta(hours=2)
        old_tasks = await sync_to_async(list)(ChatBotTask.objects.filter(
            chat_id=chat_id,
            created_at__gt=last_2_hours))
        if old_tasks:
            for old_task in old_tasks:
                old_task_id = f"ai_answer_{old_task.message_id}"
                existing_task = AsyncResult(old_task_id)
                if existing_task and existing_task.status == "PENDING":
                    existing_task.revoke(terminate=True)
                    # logger.info(f"Task {old_task_id} revoked before launching")

    async def prepare_data(self):
        message_id = self.data.get('payload').get('value').get('id')
        chat_id = self.data.get("payload").get("value").get("chat_id")
        author_id = self.data.get("payload").get("value").get("author_id")
        message = self.data.get("payload").get("value").get("content").get("text")
        time_to_work = await check_chat_bot_scheduler(self.chat_bot)
        bot_stopped_for_chat = await self.chat_shutdown_check(chat_id)
        return message_id, chat_id, author_id, message, time_to_work, bot_stopped_for_chat

    async def chat_shutdown_check(self, chat_id) -> bool:
        chat_stopped = await ChatBotTask.objects.filter(
            chat_id=chat_id,
            chat_shutdown_by_user=True,
        ).aexists()
        return chat_stopped and self.chat_bot.shutdown_after_manager

    async def post(self, request, *args, **kwargs):
        decoded_string = request.body.decode('utf-8')
        self.data = json.loads(decoded_string)

        user_id = self.data.get("payload").get("value").get("user_id")
        avito_account = await AvitoAccount.objects.aget(id=user_id)
        self.chat_bot = await AiChatBot.objects.aget(avito_account=avito_account)
        # await avito_account.update_refresh_token_async()

        if (self.data.get("payload").get("type") == "message"
                and self.data.get("payload").get("value").get("type") == "text"):  # skip system messages

            (message_id, chat_id, author_id, last_message,
             time_to_work, bot_stopped_for_chat) = await self.prepare_data()
            if bot_stopped_for_chat:
                print("!!!BOT STOPPER FOR CHAT!!!")

            if author_id != user_id and self.chat_bot.is_active and time_to_work and not bot_stopped_for_chat:  # для входящих
                await self.revoke_old_tasks(chat_id)
                new_task, created = await ChatBotTask.objects.aget_or_create(
                    chat_id=chat_id,
                    message_id=message_id,
                    avito_account=avito_account,
                    text=last_message,
                )

                if created:
                    if ENVIRONMENT == "PRODUCTION":
                        await asyncio.sleep(self.chat_bot.waiting_minutes * 60)  # WAIT TIME BEFORE ANY ACTIONS
                    ai_answer_sender_task.delay(
                        avito_account.id, chat_id, self.chat_bot.id, new_task.message_id,
                    )

            if author_id == user_id and self.chat_bot.is_active and self.chat_bot.shutdown_after_manager:  # Если исходящих
                task, created = await ChatBotTask.objects.aget_or_create(
                    avito_account=avito_account,
                    chat_id=chat_id,
                    message_id=message_id,
                    answer_text=last_message,
                )
                await self.revoke_old_tasks(chat_id)

                if created:  # Если создалась таска значит небыло ответа такого от ИИ
                    task.chat_shutdown_by_user = True  #  Останавливаем дальнейшие ответы от ИИ если человек вмешался в разговор
                    await task.asave()

        return JsonResponse({"status": "ok"}, status=200)


class SubscribeView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)  #Rauf
        await subscribe_to_messages(avito_account)
        return JsonResponse({"status": "ok"}, status=200)


class StopSubscribeView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)  #Rauf
        # await avito_account.update_refresh_token_async()
        await stop_subscribe_to_messages(avito_account)
        return JsonResponse({"status": "ok"}, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class CheckSubscribtionsView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(AvitoAccount.objects.get)(pk=145213826)  # Rauf
        await check_subscriptions(avito_account)
        return JsonResponse({"status": "ok"}, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class StatisticsDailyReportView(View):
    def get(self, request, *args, **kwargs):
        BotStatisticsDailyReportClass.statistics_sender_main_task()
        return JsonResponse({"status": "ok"}, status=200)

@method_decorator(csrf_exempt, name='dispatch')
class SummarySenderView(View):
    def get(self, request, *args, **kwargs):
        ChatBotSummaryReportClass.summary_sender_main_task.delay(163634833, "u2i-jl7kFERA8KE843KWuc4SyQ")
        return (JsonResponse({"status": "ok"}, status=200))

@method_decorator(csrf_exempt, name='dispatch')
class MiltipleFilesSenderTestView(View):
    def get(self, request, *args, **kwargs):
        PdfReportBaseClass.batch_files_sender_to_tg()
        return (JsonResponse({"status": "ok"}, status=200))




