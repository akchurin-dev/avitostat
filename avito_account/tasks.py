from asgiref.sync import async_to_sync, sync_to_async
from telegram_bot import bot
from base.celery import celery_app
from avito_account.api.get_balance import get_balance
from avito_account.models.models import AvitoAccount
from base import settings


@celery_app.task(name='avito_account.tasks.sentry_test')
def sentry_test():
    division_by_zero = 1 / 0


@celery_app.task(name='avito_account.tasks.balance_alert_send_task')
def balance_alert_send_task():
    async_to_sync(balance_alert_send)()


async def balance_alert_send():
    avito_accounts = await sync_to_async(list)(AvitoAccount.objects.filter(
        created_by__is_active=True,
        telegram_id__isnull=False))
    for avito_account in avito_accounts:
        if avito_account.balance_alerting:
            balance = await get_balance(avito_account)
            if balance < 5000:
                text = (
                    f"👤 Аккаунт: {avito_account.name}\n\n"
                    f"💼 Ваш баланс на площадке AVITO: {balance} рублей\n\n"
                    "❗️ Чтобы избежать блокировки рекламы, рекомендуем пополнить баланс заранее.\n\n"
                )

                url = f"https://www.avito.ru/account/step1"
                text += f"💳 [Пополнить через личный кабинет]({url})"

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
