import asyncio
import datetime
import time
from pprint import pprint
from pathlib import Path


import pdfkit
from jinja2 import Template

from django.db.models import Q
from django.utils import timezone
import pytz
from asgiref.sync import sync_to_async, async_to_sync
from celery.result import AsyncResult
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from avito_account.models.models import AvitoAccount, moscow_time
from base.settings import ENVIRONMENT
from chat_bot.models import AiChatBot, ChatBotTask
from chat_bot.tasks import ai_answer_sender_task, ai_answer_sender
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
import json
from base.celery import logger
from chat_bot.api.subscriptions import subscribe_to_messages, stop_subscribe_to_messages, check_subscriptions
from messaging.api import get_chats, get_chats_last_50_messages
from messaging.bad_mes_report.utils_bad_messaging_report import bad_messaging_report_generate_html, add_start_end_dates
from messaging.bad_mes_report.utils_chats import get_ready_chats, filter_chats_for_last_period, \
    filter_chats_only_with_text, filter_by_bot_answered_chat_ids

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
                    await asyncio.sleep(self.chat_bot.waiting_minutes * 60)  # WAIT TIME BEFORE ANY ACTIONS
                    ai_answer_sender_task.delay(
                        avito_account.id, user_id, chat_id, self.chat_bot.id, new_task.message_id,
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
class DailyChatsReportView(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok"}, status=200)

    def report_sender_via_celery(self, chat_id):
        statistics, chats_total = self.get_report_data()
        if statistics is not None:
            html = self.generate_html(statistics, chats_total)
            pdf_path = self.pdf_generator

    def get_report_data(self):
        avito_accounts = AvitoAccount.objects.filter(id=145213826)
        for account in avito_accounts:
            async_to_sync(account.update_refresh_token_async)()
            chats = async_to_sync(get_chats)(account, period="day")
            if chats:
                if ENVIRONMENT == "PRODUCTION":
                    last_24_hours = timezone.now() - datetime.timedelta(days=1)
                else:
                    last_24_hours = timezone.now() - datetime.timedelta(days=2)

                bot_chats = ChatBotTask.objects.filter(avito_account=account, created_at__gte=last_24_hours,)
                unique_bot_chat_ids = [chat.get("chat_id", None) for chat in bot_chats.values("chat_id").distinct() if len(bot_chats) > 0]
                contacts = bot_chats.filter(
                    Q(address__isnull=False) & ~Q(address="") |
                    Q(mobile__isnull=False) & ~Q(mobile="") |
                    Q(whatsapp__isnull=False) & ~Q(whatsapp="") |
                    Q(telegram__isnull=False) & ~Q(telegram="") |
                    Q(email__isnull=False) & ~Q(email="")
                ).values("chat_id").distinct().count()

                # Chats with messages getting
                actual_chats = async_to_sync(filter_chats_for_last_period)(chats, "day")
                actual_chats_with_mes = async_to_sync(get_chats_last_50_messages)(account, actual_chats)
                only_with_text = filter_chats_only_with_text(actual_chats_with_mes)
                chats_only_bot_answered = filter_by_bot_answered_chat_ids(only_with_text, unique_bot_chat_ids)


                statistics = {
                    "avito_account_id": account.id,  # for pdf file naming
                    "avito_account_name": account.name,
                    "total_chats_count": len(only_with_text),
                    "bot_chats_count": len(unique_bot_chat_ids),
                    "contacts_count": contacts,
                }

                return statistics, chats_only_bot_answered

    def pdf_generator(self, statistics, chats_total):
        if ENVIRONMENT == 'DEVELOPMENT':
            wkhtmltopdf_path = "/usr/local/bin/wkhtmltopdf"  # For testing 5 items  for economy
        else:
            wkhtmltopdf_path = "/usr/bin/wkhtmltopdf"

        html_content = self.generate_html(statistics, chats_total)
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        # Define the directory and file path with the date
        reports_dir = Path("chat_bot/daily_report_pdfs")
        reports_dir.mkdir(parents=True, exist_ok=True)
        # Get the current date in dd.mm.yyyy format
        current_date = datetime.datetime.now().strftime("%d.%m.%Y")
        pdf_path = reports_dir / f"daily_bot_report_{current_date}_{statistics.get("avito_account_id", "неизвестен id")}.pdf"
        pdfkit.from_string(html_content, pdf_path, configuration=config)
        return pdf_path

    def generate_html(self, statistics, chats_total):
        # Загрузка шаблона из файла
        with open("chat_bot/templates/chat_bot/daily_chats_report.html", "r", encoding="utf-8") as file:
            template_content = file.read()

        template = Template(template_content)
        # Данные для подстановки в шаблон
        avito_account_name = statistics.get('avito_account_name') if statistics else "Неизвестно"
        date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")
        # Генерация HTML с использованием шаблона и данных
        return template.render(avito_account_name=avito_account_name,
                               start_date=date,
                               end_date="delete_this_data",
                               statistics=statistics,
                               chats=chats_total or [],)

    def send_report(self, pdf_path):
        if pdf_path:
            chat_id = "-4221870448" if ENVIRONMENT=="DEVELOPMENT" else avito_account.telegram_id
            try:
                await sync_to_async(bot.send_raw, thread_sensitive=False)(
                    chat_id=chat_id,
                    function="send_document",
                    document=types.FSInputFile(pdf_path))


