from aiogram import types
from django.http import HttpResponse
from telegram_bot import bot
from django.views import View
from messaging.tasks import bad_messaging_week_report_async


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
        # TODO добавить условия для того или иного статуса, на данный момент при любом раскладе будет 200
        return HttpResponse(status=200)


class BadMessagingWeekReportAllTestView(View):
    async def get(self, request, *args, **kwargs):
        await bad_messaging_week_report_async(test_from_prod=True)
        # TODO добавить условия для того или иного статуса, на данный момент при любом раскладе будет 200
        return HttpResponse(status=200)
