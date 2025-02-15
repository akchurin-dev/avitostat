import datetime
import time
from base.settings import ENVIRONMENT
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

moscow_tz = pytz.timezone('Europe/Moscow')

@method_decorator(csrf_exempt, name='dispatch')
class WebhookInboxViewClass(View):

    @staticmethod
    def prepare_data(data, chat_bot):
        message_id = data.get('payload').get('value').get('id')
        chat_id = data.get("payload").get("value").get("chat_id")
        author_id = data.get("payload").get("value").get("author_id")
        message = data.get("payload").get("value").get("content").get("text")
        is_time_to_work = WebhookInboxViewClass.check_chat_bot_scheduler(chat_bot)
        bot_stopped_for_chat = WebhookInboxViewClass.chat_shutdown_check(chat_id, chat_bot)
        return message_id, chat_id, author_id, message, is_time_to_work, bot_stopped_for_chat

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
        return chat_stopped and chat_bot.shutdown_after_manager

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
    def incoming_messages_handler(chat_id, message_id, last_message, avito_account, chat_bot):
        WebhookInboxViewClass.revoke_ai_answer_old_tasks(chat_id)
        new_task, created = ChatBotTask.objects.get_or_create(
            chat_id=chat_id,
            message_id=message_id,
            avito_account=avito_account,
            text=last_message,
        )

        if created:
            if ENVIRONMENT == "PRODUCTION":
                time.sleep(chat_bot.waiting_minutes * 60)  # WAIT TIME BEFORE ANY ACTIONS
            AiAnswerAvitoClass.ai_answer_sender_task.delay(avito_account.id, chat_id, chat_bot.id, new_task.message_id)

    @staticmethod
    def outgoing_messages_handler(chat_id, message_id, last_message, avito_account):
        WebhookInboxViewClass.revoke_ai_answer_old_tasks(chat_id)  # Вдруг были старые задачи из-за входящих сообщений для ответа ИИ
        #TODO отмена предыдущих тасок для саммари для данного чата
        contacts = AiAnswerAvitoClass.chat_contacts_checker_task(avito_account, chat_id)
        AiAnswerAvitoClass.chat_bot_task_save(ai_answer=contacts,
                                              new_task_id=message_id,
                                              avito_account_id=avito_account.id)
        if contacts:
            if ENVIRONMENT == "PRODUCTION":
                time.sleep(300)  # 300 by default
            ChatBotSummaryReportClass.summary_sender_main_task.delay(avito_account.id, chat_id)


        # Логика остановки бота если человек вмешался в разговор
        task, created = ChatBotTask.objects.get_or_create(
            avito_account=avito_account,
            chat_id=chat_id,
            message_id=message_id,
            answer_text=last_message,
        )
        if created:  # Если создалась таска значит небыло ответа такого от ИИ
            task.chat_shutdown_by_user = True  # Останавливаем дальнейшие ответы от ИИ если человек вмешался в разговор
            task.save()

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode('utf-8'))
        user_id = data.get("payload").get("value").get("user_id")
        avito_account = AvitoAccount.objects.get(id=user_id)
        chat_bot = AiChatBot.objects.get(avito_account=avito_account)

        if (data.get("payload").get("type") == "message"
                and data.get("payload").get("value").get("type") == "text"):  # skip system messages

            message_id, chat_id, author_id, last_message, is_time_to_work, bot_stopped_for_chat =\
                WebhookInboxViewClass.prepare_data(data, chat_bot)

            incoming_mgs = author_id != user_id

            # для входящих сообщений
            if incoming_mgs  and chat_bot.is_active and is_time_to_work and not bot_stopped_for_chat:
                WebhookInboxViewClass.incoming_messages_handler(chat_id, message_id, last_message, avito_account, chat_bot)

            # Для исходящих
            if not incoming_mgs and chat_bot.is_active:
                WebhookInboxViewClass.outgoing_messages_handler(chat_id, message_id, last_message, avito_account)


            if bot_stopped_for_chat: print("!!!BOT STOPPER FOR CHAT!!!")  # TODO: remove after testing
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
        ChatBotSummaryReportClass.summary_sender_main_task.delay(163634833, "u2i-jl7kFERA8KE843KWuc4SyQ")
        return (JsonResponse({"status": "ok"}, status=200))

@method_decorator(csrf_exempt, name='dispatch')
class MiltipleFilesSenderTestView(View):
    def get(self, request, *args, **kwargs):
        PdfReportBaseClass.batch_files_sender_to_tg_not_used()
        return (JsonResponse({"status": "ok"}, status=200))



