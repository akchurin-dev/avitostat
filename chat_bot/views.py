import datetime
import json

from celery import shared_task
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

from amo_a5client import amo_a5client
from avito_account.models.models import AvitoAccount
from base.settings import ENVIRONMENT
from chat_bot.tasks import ai_answer_sender_task
from chat_bot.tasks import outgoing_messages_handler
from chat_bot.models import AiChatBot, AvitoTaskStatus, ChatBotTask
from chat_bot.utils import avito_api
from chat_bot.utils import avito_chatbots
from utils.logging import new_trace_id, TraceLogger


@method_decorator(csrf_exempt, name='dispatch')
class WebhookInboxViewClass(View):
    def post(self, request, *args, **kwargs):
        request_data = json.loads(request.body.decode('utf-8'))
        WebhookInboxViewClass.webhook_processing_task.delay(request_data, trace_id=new_trace_id())
        return JsonResponse({"status": "ok"}, status=200)

    @staticmethod
    @shared_task
    def webhook_processing_task(request_data, *, trace_id: str):
        tlogger = TraceLogger(trace_id)
        tlogger.info({"new avito callback": request_data})

        try:
            chat_id = request_data["payload"]["value"]["chat_id"]
            request_id = request_data["id"]
            message_id = request_data["payload"]["value"]["id"]
            text = request_data["payload"]["value"]["content"].get("text", "")
            author_id = request_data["payload"]["value"]["author_id"]
            user_id = request_data["payload"]["value"]["user_id"]
            created_at_timestamp = request_data["payload"]["value"]["created"]
            message_type = request_data["payload"]["value"]["type"]
        except:
            tlogger.info("Error when parse request data")
            raise

        amo_avito_accounts_link = amo_a5client.get_amo_avito_accounts_link(user_id)
        if amo_avito_accounts_link:
            amo_a5client.handle_message_from_avito.delay(
                avito_account_id=user_id,
                amo_account_id=amo_avito_accounts_link.amo_account.pk,
                chat_id=chat_id,
                message_id=message_id,
                message_created_at_timestamp=created_at_timestamp,
                text=text,
                message_type=message_type,
                trace_id=tlogger.trace_id,
            )
            return

        incoming_msg = author_id != user_id
        avito_account = AvitoAccount.objects.filter(id=user_id).first()

        if avito_account is None:
            tlogger.info(f"Stop handling. AvitoAccount with id = {user_id} not found")
            return

        tlogger.info(f"New message callback for avito account '{avito_account.name}'")

        tlogger.info(f"Request id - {request_id}")
        tlogger.info(f"account - {avito_account.name}")
        tlogger.info(f"Request text - {text}")
        tlogger.info(f"is_incoming - {incoming_msg}")

        new_task, created = ChatBotTask.objects.get_or_create(
            avito_account=avito_account,
            chat_id=chat_id,
            message_id=message_id,
            message_created_at=datetime.datetime.fromtimestamp(created_at_timestamp, datetime.timezone.utc),
            text=text,
            defaults={
                "status": AvitoTaskStatus.CREATED.value,
            },
        )
        if not created:
            tlogger.info(f"Stop handling. Request already processed: message_id - {new_task.message_id}")
            return

        chatbot = AiChatBot.objects.filter(account=avito_account).first()

        if chatbot is None:
            cancel_message = "Chatbot not found"
            new_task.cancel(cancel_message, save=True)
            tlogger.info("Stop handling. " +cancel_message)
            return

        if not chatbot.is_active:
            cancel_message = "Chatbot is inactive"
            new_task.cancel(cancel_message, save=True)
            tlogger.info("Stop handling. " + cancel_message)
            return

        if ENVIRONMENT != "PRODUCTION":
            avito_account.update_refresh_token()

        request_type = request_data["payload"]["type"]
        message_type = request_data["payload"]["value"]["type"]

        if request_type != "message":
            cancel_message = f"Unexpected request type, got {request_type}"
            new_task.cancel(cancel_message, save=True)
            tlogger.info(f"Stop handling. " + cancel_message)
            return

        if message_type != "text":
            cancel_message = f"Unexpected message type, got {message_type}"
            new_task.cancel(cancel_message, save=True)
            tlogger.info(f"Stop handling. " + cancel_message)
            return

        # Исходящие сообщения
        if not incoming_msg:
            outgoing_messages_handler.s(
                chat_id=chat_id,
                message_id=message_id,
                account_id=avito_account.pk,
                chatbot_id=chatbot.pk,
                task_id=new_task.pk,
                trace_id=tlogger.trace_id,
            ).apply_async(countdown=30)
            return

        if not avito_chatbots.check_chatbot_worktime_now(chatbot):
            cancel_message = "It isn't chatbot worktime"
            new_task.cancel(cancel_message, save=True)
            tlogger.info("Stop handling. " + cancel_message)
            return

        if avito_chatbots.check_chatbot_shutdown_for_chat(chat_id, chatbot, tlogger=tlogger):
            cancel_message = "Chatbot is stopped for chat"
            new_task.cancel(cancel_message, save=True)
            tlogger.info("Stop handling. " + cancel_message)
            return

        avito_api.read_chat(avito_account, chat_id, tlogger=tlogger)

        tlogger.info(f"Wait for {chatbot.waiting_seconds} seconds...")

        ai_answer_sender_task.s(
        # ai_answer_sender_task(
            avito_account_id=avito_account.pk,
            chatbot_id=chatbot.pk,
            chat_id=chat_id,
            message_id=message_id,
            new_task_id=new_task.message_id,
            trace_id=tlogger.trace_id,
        ).apply_async(countdown=chatbot.waiting_seconds)


#TODO Manual testing endpoints
@method_decorator(csrf_exempt, name='dispatch')
class StatisticsDailyReportView(View):
    def get(self, request, *args, **kwargs):
        # BotStatisticsDailyReportClass.statistics_sender_main_task.delay()
        return JsonResponse({"status": "ok"}, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class SummarySenderView(View):
    def get(self, request, *args, **kwargs):
        # ChatBotSummaryReportClass.summary_sender_main_task(163634833, "u2i-jl7kFERA8KE843KWuc4SyQ")
        return (JsonResponse({"status": "ok"}, status=200))


@method_decorator(csrf_exempt, name='dispatch')
class MiltipleFilesSenderTestView(View):
    def get(self, request, *args, **kwargs):
        # PdfReportBaseClass.batch_files_sender_to_tg_not_used()
        return (JsonResponse({"status": "ok"}, status=200))
