from aiogram import types
from telegram_bot import bot
from avito_account.models import AvitoAccount
from messaging.api import get_chats, get_chats_messages
from django.http import JsonResponse, HttpResponse
from django.views import View
from jinja2 import Template
from weasyprint import HTML
from asgiref.sync import sync_to_async

from messaging.bad_mes_report.utils_open_ai import compare_messages_for_ai, analyze_overall_conversation
from messaging.tasks import bad_messaging_week_report_async
from messaging.views import get_chats_for_last_week


class TelegramSenderTestView(View):
    def get(self, request):
        bot.send_raw(chat_id="-1002061228822", text="TEST TEXT")


class TelegramDocumentSenderTestView(View):
    def get(self, request):
        bot.send_raw(
            chat_id="-1002061228822",
            function="send_document",
            document=types.FSInputFile("deep_tests/test.pdf"),
        )


class BadMessagingWeekReportTestView(View):
    async def get(self, request, *args, **kwargs):
        avito_accounts_id = kwargs.get("avito_accounts_id", None)
        await bad_messaging_week_report_async(test_from_prod=True, only_for_users=[avito_accounts_id])


class BadMessagingWeekReportAllTestView(View):
    async def get(self, request, *args, **kwargs):
        await bad_messaging_week_report_async(test_from_prod=True)
