from asgiref.sync import async_to_sync, sync_to_async
from celery import shared_task
from telegram_bot import bot

from avito_account.api.get_balance import get_balance
from avito_account.models.models import AvitoAccount
from base import settings


@shared_task
def send_balance_alert_task(avito_account_id):
    async_to_sync(send_balance_alert)(avito_account_id)


async def send_balance_alert(avito_account_id):
    avito_account = await AvitoAccount.objects.aget(pk=avito_account_id)
    if avito_account.balance_alerting:
        balance = await get_balance(avito_account)
        if balance < 5000:
            text = (f"💼 Ваш баланс на площадке AVITO: {balance} рублей\n\n"
                    "❗️ Чтобы избежать блокировки рекламы, рекомендуем пополнить баланс заранее.\n\n"
                    "💳 Пополнение доступно в любое время в вашем личном кабинете!")

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
