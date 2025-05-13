import json
from typing import NamedTuple

from asgiref.sync import sync_to_async, async_to_sync
from celery import shared_task
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.timezone import now, is_naive
from django.views import View

from avito_account.models.models import AvitoAccount
from base.settings import ENVIRONMENT
from chat_bot import ai_utils
from chat_bot.api.core import AvitoMessengerSync
from chat_bot.tasks import BotStatisticsDailyReportClass, ChatBotSummaryReportClass, PdfReportBaseClass, \
    AiAnswerAvitoClass
from chat_bot.api.subscriptions import subscribe_to_messages, stop_subscribe_to_messages, check_subscriptions
from chat_bot.models import AiChatBot, ChatBotTask
from chat_bot.utils import avito_chatbots
from chat_bot.utils import companies_branches
from messaging.api import MessagingAPISync
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

        try:
            chat_id = request_data["payload"]["value"]["chat_id"]
            request_id = request_data["id"]
            message_id = request_data["payload"]["value"]["id"]
            text = request_data["payload"]["value"]["content"].get("text", "Не предусмотрено")
            author_id = request_data["payload"]["value"]["author_id"]
            user_id = request_data["payload"]["value"]["user_id"]
        except:
            tlogger.info({
                "title": "Error when parse request data",
                "request_data": request_data,
            })
            raise

        incoming_msg = author_id != user_id
        avito_account = AvitoAccount.objects.filter(id=user_id).first()

        if avito_account is None:
            tlogger.info(f"Stop handling. AvitoAccount with id = {user_id} not found")
            return

        chatbot = AiChatBot.objects.filter(account=avito_account).first()

        if chatbot is None:
            tlogger.info(f"Stop handling. Chatbot for account '{avito_account.name}' not found")
            return

        if not chatbot.is_active:
            tlogger.info("Stop handling. Chatbot is inactive")
            return

        if avito_account is None:
            tlogger.info(f"Stop handling. AvitoAccount (id={user_id}) isn't found")
            return

        if ENVIRONMENT != "PRODUCTION":
            async_to_sync(avito_account.update_refresh_token_async)()

        tlogger.info(f"Request id - {request_id}")
        tlogger.info(f"account - {avito_account.name}")
        tlogger.info(f"Request text - {text}")
        tlogger.info(f"is_incoming - {incoming_msg}")

        new_task, created = ChatBotTask.objects.get_or_create(
            avito_account=avito_account,
            chat_id=chat_id,
            message_id=message_id,
            text=text,
        )

        if not created:
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

        # Исходящие сообщения
        if not incoming_msg:
            WebhookInboxViewClass.outgoing_messages_handler(
                chat_id=chat_id,
                message_id=message_id,
                avito_account=avito_account,
                chatbot=chatbot,
                new_task=new_task,
                trace_id=tlogger.trace_id,
            )
            return

        if chatbot.read_only:
            tlogger.info("Stop handling. Chatbot configured as readonly")
            return

        if not avito_chatbots.check_chatbot_worktime_now(chatbot):
            tlogger.info(f"Stop handling. It isn't worktime for chatbot '{chatbot.name}'")
            return

        if avito_chatbots.check_chatbot_shutdown_for_chat(chat_id, chatbot, tlogger=tlogger):
            tlogger.info("Stop handling. Chatbot is stopped for chat")
            return

        AvitoMessengerSync.read_chat(avito_account, user_id, chat_id)
        WebhookInboxViewClass.incoming_messages_handler(
            new_task=new_task,
            chat_id=chat_id,
            message_id=message_id,
            avito_account=avito_account,
            chatbot=chatbot,
            tlogger=tlogger,
        )

    @staticmethod
    def incoming_messages_handler(
        new_task: ChatBotTask,
        chat_id: str,
        message_id: str,
        avito_account: AvitoAccount,
        chatbot: AiChatBot,
        *,
        tlogger: TraceLogger,
    ) -> None:

        tlogger.info(f"Wait for {chatbot.waiting_seconds} seconds...")

        AiAnswerAvitoClass.ai_answer_sender_task.s(
            avito_account_id=avito_account.pk,
            chatbot_id=chatbot.pk,
            chat_id=chat_id,
            message_id=message_id,
            new_task_id=new_task.message_id,
            trace_id=tlogger.trace_id,
        ).apply_async(countdown=chatbot.waiting_seconds)

    @staticmethod
    def outgoing_messages_handler(
        chat_id: str,
        message_id: str,
        avito_account: AvitoAccount,
        chatbot: AiChatBot,
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

        chat = MessagingAPISync.get_chat_last_50_messages_by_chat_id(
            avito_account=avito_account,
            chat_id=chat_id,
            trace_id=tlogger.trace_id,
        )
        assert "messages" in chat

        last_message_id = chat["messages"][-1]["id"]
        if chat["messages"][-1]["type"] == "system":
            last_message_id = chat["messages"][-2]["id"]

        if last_message_id != message_id:
            tlogger.info(f"Stop handling. Message (id={message_id}) is not actual")
            return

        company_branch = companies_branches.define_company_branch(avito_account, chat_id)

        ai_answer = ai_utils.ai_answer_with_contacts_typed(
            ai_assistant=chatbot,
            chat=chat["messages"],
            ask_location=company_branch is None,
            tlogger=tlogger,
        )
        AiAnswerAvitoClass.task_contacts_save(message_id, ai_answer, is_incoming=False, company_branch=company_branch)

        if chatbot.send_new_contact_report and ai_answer.contacts:
            tlogger.info(f"Contacts found - {ai_answer.contacts.model_dump()}")
            tlogger.info("Send report")
            ChatBotSummaryReportClass.summary_sender_main_task(avito_account.pk, chat_id, trace_id=tlogger.trace_id)
        else:
            tlogger.info({
                "title": "Don't send contacts",
                "chatbot.send_new_contact_report": chatbot.send_new_contact_report,
                "contacts": ai_answer.contacts.model_dump() if ai_answer.contacts else None,
            })

        # Логика остановки бота если человек вмешался в разговор
        if chatbot.shutdown_after_manager:
            #INFO идея если на след день пишет человек то бот не должен останавливаться и время указывается
            new_task.chat_shutdown_by_user = True  # Останавливаем дальнейшие ответы от ИИ если человек вмешался
            new_task.save()
            tlogger.info("Bot successfully disabled after manager")


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



