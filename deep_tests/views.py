from aiogram import types
from django.http import HttpResponse
from telegram_bot import bot
from django.views import View
from messaging.tasks import bad_messaging_report_by_period, bad_messaging_week_report_async_task


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
        await bad_messaging_report_by_period(test_from_prod=True, only_for_users=[avito_accounts_id])
        # TODO Придумать нормальные условия для 200 и других статусов, тк сейчас всегда 200
        return HttpResponse(status=200)


class BadMessagingWeekReportAllTestView(View):
    def get(self, request, *args, **kwargs):
        bad_messaging_week_report_async_task.delay(test_from_prod=True)
        # TODO Придумать нормальные условия для 200 и других статусов, тк сейчас всегда 200
        return HttpResponse(status=200)
