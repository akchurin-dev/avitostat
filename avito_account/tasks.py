from asgiref.sync import async_to_sync, sync_to_async
from celery import shared_task
from telegram_bot import bot

from avito_account.models.models import AvitoAccount
from base import settings


@shared_task
def send_balance_alert_task(avito_account_id, chat_id):
    async_to_sync(send_balance_alert)(avito_account_id, chat_id)


async def send_balance_alert(avito_account_id, chat_id):
    avito_accounts = await AvitoAccount.objects.aall()
    for avito_account in avito_accounts:
        text = ("🆕 Новый клиент из AVITO\n\n"
                "📋 Сводка по переписке:\n\n")
        if settings.ENVIRONMENT == 'DEVELOPMENT':
            chat_id = "-4221870448"
        else:
            chat_id = avito_account.telegram_id

        while text:
            await sync_to_async(bot.send_raw, thread_sensitive=False)(
                chat_id=chat_id,
                function="send_message",
                text=text,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            text = text[4000:]
