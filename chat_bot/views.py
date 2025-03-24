import datetime
import logging
import time
from pprint import pprint

from celery import shared_task

from base.celery import celery_logger
from base.settings import ENVIRONMENT
from chat_bot.api.core import AvitoMessengerSync
from chat_bot.tasks import BotStatisticsDailyReportClass, ChatBotSummaryReportClass, PdfReportBaseClass, \
    AiAnswerAvitoClass
import pytz
from asgiref.sync import sync_to_async, async_to_sync
from celery.result import AsyncResult
from django.utils.timezone import now, is_naive
from django.views.decorators.csrf import csrf_exempt
from avito_account.models.models import AvitoAccount
from chat_bot.models import AiChatBot, ChatBotTask
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
import json
from chat_bot.api.subscriptions import subscribe_to_messages, stop_subscribe_to_messages, check_subscriptions
from utils.logging import new_trace_id, TraceLogger


moscow_tz = pytz.timezone('Europe/Moscow')
logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookInboxViewClass(View):

    @staticmethod
    def message_data(data):
        #From request
        chat_id = data.get("payload").get("value").get("chat_id")
        message_id = data.get('id')
        author_id = data.get("payload").get("value").get("author_id")
        user_id = data.get("payload").get("value").get("user_id")
        text = data.get("payload").get("value").get("content").get("text", "Не предусмотрено")
        incoming_mgs = author_id != user_id

        #Objects
        avito_account = AvitoAccount.objects.get(id=user_id)
        chat_bot = AiChatBot.objects.get(avito_account=avito_account)

        # Service data
        is_time_to_work = WebhookInboxViewClass.check_chat_bot_scheduler(chat_bot)
        bot_stopped_for_chat = WebhookInboxViewClass.chat_shutdown_check(chat_id, chat_bot)

        return chat_id, message_id, author_id, user_id, text, incoming_mgs, avito_account, chat_bot, is_time_to_work, bot_stopped_for_chat

    @staticmethod
    def check_chat_bot_scheduler(chat_bot: AiChatBot) -> bool:
        now = datetime.datetime.now(tz=moscow_tz)
        start = moscow_tz.localize(datetime.datetime.combine(now.date(), chat_bot.work_time_from))
        # Если рабочее время заканчивается на следующий день
        if chat_bot.work_time_to < chat_bot.work_time_from:
            stop = moscow_tz.localize(
                datetime.datetime.combine(now.date() + datetime.timedelta(days=1), chat_bot.work_time_to))
        else:
            stop = moscow_tz.localize(datetime.datetime.combine(now.date(), chat_bot.work_time_to))
        return start <= now <= stop

    @staticmethod
    def chat_shutdown_check(chat_id, chat_bot) -> bool:
        chat_stopped = ChatBotTask.objects.filter(chat_id=chat_id, chat_shutdown_by_user=True,).exists()
        stopped = chat_stopped and chat_bot.shutdown_after_manager
        if stopped:
            celery_logger.warning(f"chat_stopped by manager manually answers - {chat_stopped}")
        else:
            celery_logger.info(f"chat_stopped by manager manually answers - {chat_stopped}")
        return stopped

    @staticmethod
    def revoke_ai_answer_old_tasks(chat_id: str):
        current_time = now().astimezone(moscow_tz)
        last_2_hours = current_time - datetime.timedelta(hours=2)
        old_tasks = ChatBotTask.objects.filter(
            chat_id=chat_id,
            created_at__gt=last_2_hours)
        if old_tasks:
            for old_task in old_tasks:
                old_task_id = f"ai_answer_{old_task.message_id}"
                existing_task = AsyncResult(old_task_id)
                if existing_task and existing_task.status == "PENDING":
                    existing_task.revoke(terminate=True)

    @staticmethod
    def incoming_messages_handler(new_task, chat_id, avito_account, chat_bot, *, tlogger: TraceLogger):
        WebhookInboxViewClass.revoke_ai_answer_old_tasks(chat_id)
        wait_sec = chat_bot.waiting_minutes * 60

        if ENVIRONMENT == "DEVELOPMENT":
            wait_sec //= 2

        if ENVIRONMENT == "TESTING":
            wait_sec = 10

        tlogger.info(f"Wait for {wait_sec} seconds...")
        time.sleep(wait_sec)

        AiAnswerAvitoClass.ai_answer_sender_task.delay(
            avito_account_id=avito_account.id,
            chat_id=chat_id,
            chat_bot_id=chat_bot.id,
            new_task_id=new_task.message_id,
            trace_id=tlogger.trace_id,
        )

    @staticmethod
    @shared_task
    def outgoing_messages_handler(chat_id, message_id, avito_account, chat_bot, new_task, trace_id: str | None = None):
        tlogger = TraceLogger(trace_id)
        tlogger.info("Start outgoing_messages_handler")

        # TODO отмена предыдущих тасок для саммари для данного чата ПРОВЕРИТЬ КАК ТО через флауэр
        new_task.is_incoming = False
        new_task.save()
        WebhookInboxViewClass.revoke_ai_answer_old_tasks(chat_id)  # Вдруг были старые задачи из-за входящих сообщений для ответа ИИ

        #Checking answered from AI
        tasks = list(ChatBotTask.objects.filter(chat_id=chat_id, is_incoming=True).order_by("created_at"))
        answered_from_ai = False

        for task in tasks[-5:]:
            if task.answer_text and task.answer_text == new_task.text:
                answered_from_ai = True
                break

        tlogger.info(f"Current outgoing message: '{new_task.text}'")
        tlogger.info(f"Last answers: " + str([task.answer_text for task in tasks[-5:]]))

        if answered_from_ai:
            tlogger.info("Stop handling. Message generated by ai")
            return

        tlogger.info("Message wrote by manager manually")

        contacts = AiAnswerAvitoClass.chat_contacts_checker_task(avito_account, chat_id, trace_id=tlogger.trace_id)
        AiAnswerAvitoClass.task_contacts_save(message_id, contacts, is_incoming=False)

        if contacts and contacts.get("contacts") is not None:
            tlogger.info(f"Contacts found Contacts found Contacts found - {contacts}")
            ChatBotSummaryReportClass.summary_sender_main_task(avito_account.id, chat_id, trace_id=tlogger.trace_id)
        else:
            tlogger.info(F"Contacts is empty, got {contacts}")

        # Логика остановки бота если человек вмешался в разговор
        if chat_bot.shutdown_after_manager:
            #INFO идея если на след день пишет человек то бот не должен останавливаться и время указывается
            new_task.chat_shutdown_by_user = True  # Останавливаем дальнейшие ответы от ИИ если человек вмешался
            new_task.save()
            tlogger.info("Bot successfully disabled after manager")

    @staticmethod
    @shared_task
    def webhook_processing_task(request_data, *, trace_id: str):
        tlogger = TraceLogger(trace_id)
        
        (chat_id, message_id, author_id, user_id, text, is_incoming, avito_account, chat_bot,
         is_time_to_work, bot_stopped_for_chat) = WebhookInboxViewClass.message_data(request_data)
        if ENVIRONMENT != "PRODUCTION":
            async_to_sync(avito_account.update_refresh_token_async)()

        tlogger.info(f"Request id - {message_id}")
        tlogger.info(f"account - {avito_account.name}")
        tlogger.info(f"Request text - {text}")
        tlogger.info(f"is_incoming - {is_incoming}")

        new_task, created = ChatBotTask.objects.get_or_create(
            avito_account=avito_account, chat_id=chat_id, message_id=message_id, text=text,)

        if not created: # Значит уже была создана таска и сообщение было обработано как вх так и исх
            tlogger.info(f"Stop handling. Request already processed: message_id - {new_task.message_id}")
            return

        request_type = request_data["payload"]["type"]
        message_type = request_data["payload"]["value"]["type"]

        if request_type != "message":
            tlogger.info(f"Stop handling. Unexpected request type, got {request_type}")
            return

        if message_type != "text":
            tlogger.info(f"Stop handling. Unexpected message type, got {message_type}")
            return

        if not chat_bot.is_active:
            tlogger.info("Stop handling. AIChatBot inactive")
            return

        # Исходящие сообщения
        if not is_incoming:
            WebhookInboxViewClass.outgoing_messages_handler(
                chat_id=chat_id,
                message_id=message_id,
                avito_account=avito_account,
                chat_bot=chat_bot,
                new_task=new_task,
                trace_id=tlogger.trace_id,
            )
            return

        if not is_time_to_work:
            tlogger.info("Stop handling. AIChatBot out of work time")
            return

        if bot_stopped_for_chat:
            tlogger.info("Stop handling. Bot stopped for chat")
            return

        AvitoMessengerSync.read_chat(avito_account, user_id, chat_id)
        WebhookInboxViewClass.incoming_messages_handler(new_task, chat_id, avito_account, chat_bot, tlogger=tlogger)

    def post(self, request, *args, **kwargs):
        request_data = json.loads(request.body.decode('utf-8'))
        WebhookInboxViewClass.webhook_processing_task.delay(request_data, trace_id=new_trace_id())
        return JsonResponse({"status": "ok"}, status=200)


#TODO Admin panel endpoints
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

#TODO Manual testing endpoints
@method_decorator(csrf_exempt, name='dispatch')
class StatisticsDailyReportView(View):
    def get(self, request, *args, **kwargs):
        BotStatisticsDailyReportClass.statistics_sender_main_task.delay()
        return JsonResponse({"status": "ok"}, status=200)

@method_decorator(csrf_exempt, name='dispatch')
class SummarySenderView(View):
    def get(self, request, *args, **kwargs):
        ChatBotSummaryReportClass.summary_sender_main_task(163634833, "u2i-jl7kFERA8KE843KWuc4SyQ")
        return (JsonResponse({"status": "ok"}, status=200))

@method_decorator(csrf_exempt, name='dispatch')
class MiltipleFilesSenderTestView(View):
    def get(self, request, *args, **kwargs):
        PdfReportBaseClass.batch_files_sender_to_tg_not_used()
        return (JsonResponse({"status": "ok"}, status=200))



