import datetime
import json
from typing import NamedTuple

from asgiref.sync import sync_to_async, async_to_sync
from celery import shared_task
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.timezone import now, is_naive
from django.views import View
import pytz

from avito_account.models.models import AvitoAccount
from base.settings import ENVIRONMENT
from chat_bot import ai_utils
from chat_bot.api.core import AvitoMessengerSync
from chat_bot.avito_aichatbottasks import get_object_id
from chat_bot.tasks import BotStatisticsDailyReportClass, ChatBotSummaryReportClass, PdfReportBaseClass, \
    AiAnswerAvitoClass
from chat_bot.api.subscriptions import subscribe_to_messages, stop_subscribe_to_messages, check_subscriptions
from chat_bot.models import AiChatBot, ChatBotTask
from messaging.api import MessagingAPISync
from utils.logging import new_trace_id, TraceLogger


moscow_tz = pytz.timezone('Europe/Moscow')


@method_decorator(csrf_exempt, name='dispatch')
class WebhookInboxViewClass(View):
    class MessageData(NamedTuple):
        chat_id: str
        request_id: str
        message_id: str
        author_id: int
        user_id: int
        text: str
        incoming_msg: bool
        avito_account: AvitoAccount | None
        chat_bot: AiChatBot | None
        is_time_to_work: bool
        bot_stopped_for_chat: bool

    @staticmethod
    def message_data(data, *, tlogger: TraceLogger) -> MessageData:
        #From request
        chat_id = data.get("payload").get("value").get("chat_id")
        request_id = data.get('id')
        message_id = data["payload"]["value"]["id"]
        author_id = data.get("payload").get("value").get("author_id")
        user_id = data.get("payload").get("value").get("user_id")
        text = data.get("payload").get("value").get("content").get("text", "Не предусмотрено")
        incoming_mgs = author_id != user_id

        #Objects
        avito_account = AvitoAccount.objects.filter(id=user_id).first()

        chat_bot = None
        if avito_account:
            chat_bot = AiChatBot.objects.filter(avito_account=avito_account).first()

        # Service data
        is_time_to_work = True
        bot_stopped_for_chat = True

        if chat_bot:
            is_time_to_work = WebhookInboxViewClass.check_chat_bot_scheduler(chat_bot)
            bot_stopped_for_chat = WebhookInboxViewClass.chat_shutdown_check(chat_id, chat_bot, tlogger=tlogger)

        return WebhookInboxViewClass.MessageData(
            chat_id=chat_id,
            request_id=request_id,
            message_id=message_id,
            author_id=author_id,
            user_id=user_id,
            text=text,
            incoming_msg=incoming_mgs,
            avito_account=avito_account,
            chat_bot=chat_bot,
            is_time_to_work=is_time_to_work,
            bot_stopped_for_chat=bot_stopped_for_chat,
        )

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
    def chat_shutdown_check(chat_id, chat_bot: AiChatBot, *, tlogger: TraceLogger) -> bool:
        chat_stopped = ChatBotTask.objects.filter(chat_id=chat_id, chat_shutdown_by_user=True,).exists()
        stopped = chat_stopped and chat_bot.shutdown_after_manager
        if stopped:
            tlogger.info(f"chat_stopped by manager manually answers - {chat_stopped}")
        else:
            tlogger.info(f"chat_stopped by manager manually answers - {chat_stopped}")
        return stopped

    @staticmethod
    def incoming_messages_handler(
        new_task: ChatBotTask,
        chat_id: str,
        message_id: str,
        avito_account: AvitoAccount,
        chat_bot: AiChatBot,
        *,
        tlogger: TraceLogger,
    ) -> None:

        wait_sec = chat_bot.waiting_minutes * 60

        if ENVIRONMENT == "DEVELOPMENT":
            wait_sec //= 60

        if ENVIRONMENT == "TESTING":
            wait_sec = 10

        tlogger.info(f"Wait for {wait_sec} seconds...")

        AiAnswerAvitoClass.ai_answer_sender_task.s(
            avito_account_id=avito_account.pk,
            chat_id=chat_id,
            message_id=message_id,
            chat_bot_id=chat_bot.pk,
            new_task_id=new_task.message_id,
            trace_id=tlogger.trace_id,
        ).apply_async(countdown=wait_sec)

    @staticmethod
    def outgoing_messages_handler(
        chat_id: str,
        message_id: str,
        avito_account: AvitoAccount,
        chat_bot: AiChatBot,
        new_task: ChatBotTask,
        trace_id: str,
    ) -> None:
        tlogger = TraceLogger(trace_id)
        tlogger.info("Start outgoing_messages_handler")

        # TODO отмена предыдущих тасок для саммари для данного чата ПРОВЕРИТЬ КАК ТО через флауэр
        new_task.is_incoming = False
        new_task.save()

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

        messages = MessagingAPISync.get_chat_last_50_messages_by_chat_id(
            avito_account=avito_account,
            chat_id=chat_id,
            trace_id=tlogger.trace_id,
        )

        last_message_id = messages[-1]["id"]
        if messages[-1]["type"] == "system":
            last_message_id = messages[-2]["id"]

        if last_message_id != message_id:
            tlogger.info(f"Stop handling. Message (id={message_id}) is not actual")
            return

        ai_answer = ai_utils.ai_answer_with_contacts_typed(chat_bot, messages)
        AiAnswerAvitoClass.task_contacts_save(message_id, ai_answer, is_incoming=False)

        if ai_answer.contacts:
            tlogger.info(f"Contacts found - {ai_answer.contacts.model_dump()}")
            ChatBotSummaryReportClass.summary_sender_main_task(avito_account.pk, chat_id, trace_id=tlogger.trace_id)
        else:
            tlogger.info(f"Contacts is empty, got {ai_answer.model_dump()}")

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
        
        data = WebhookInboxViewClass.message_data(request_data, tlogger=tlogger)

        if data.avito_account is None:
            tlogger.info(f"Stop handling. AvitoAccount (id={data.user_id}) isn't found")
            return

        if data.chat_bot is None:
            tlogger.info(f"Stop handling. Chatbot linked with AvitoAccount {data.avito_account} isn't found")
            return

        if ENVIRONMENT != "PRODUCTION":
            async_to_sync(data.avito_account.update_refresh_token_async)()

        tlogger.info(f"Request id - {data.request_id}")
        tlogger.info(f"account - {data.avito_account.name}")
        tlogger.info(f"Request text - {data.text}")
        tlogger.info(f"is_incoming - {data.incoming_msg}")

        new_task, created = ChatBotTask.objects.get_or_create(
            avito_account=data.avito_account,
            chat_id=data.chat_id,
            message_id=data.message_id,
            text=data.text,
        )

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

        if not data.chat_bot.is_active:
            tlogger.info("Stop handling. AIChatBot inactive")
            return

        # Исходящие сообщения
        if not data.incoming_msg:
            WebhookInboxViewClass.outgoing_messages_handler(
                chat_id=data.chat_id,
                message_id=data.message_id,
                avito_account=data.avito_account,
                chat_bot=data.chat_bot,
                new_task=new_task,
                trace_id=tlogger.trace_id,
            )
            return

        if not data.is_time_to_work:
            tlogger.info("Stop handling. AIChatBot out of work time")
            return

        if data.bot_stopped_for_chat:
            tlogger.info("Stop handling. Bot stopped for chat")
            return

        if data.chat_bot.read_only:
            tlogger.info("Stop handling. Bot configured to read only")
            return

        AvitoMessengerSync.read_chat(data.avito_account, data.user_id, data.chat_id)
        WebhookInboxViewClass.incoming_messages_handler(
            new_task=new_task,
            chat_id=data.chat_id,
            message_id=data.message_id,
            avito_account=data.avito_account,
            chat_bot=data.chat_bot,
            tlogger=tlogger,
        )

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



