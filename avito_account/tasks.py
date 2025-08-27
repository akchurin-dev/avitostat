from asgiref.sync import async_to_sync, sync_to_async
from celery import shared_task
from telegram_bot import bot

from avito_account import oauth_utils
from avito_account.models.models import AvitoAccount
from avito_account.utils.avito_webhooks import update_avito_webhook_subscription
from base import settings
from base.celery import celery_app
from base.celery import celery_logger
from chat_bot.utils import avito_api
from utils.logging import TraceLogger


@celery_app.task(name='avito_account.tasks.sentry_test')
def sentry_test():
    division_by_zero = 1 / 0


@celery_app.task(name='avito_account.tasks.update_tokens')
def update_tokens_task(accounts_ids: list[int] | None = None):
    accounts = AvitoAccount.objects.all()
    if accounts_ids:
        accounts = accounts.filter(id__in=accounts_ids)

    for account in accounts:
        try:
            account.update_refresh_token()

            assert account.access_token
            account_info = oauth_utils.get_avito_account_info(account.access_token)
            account.profile_url = account_info["profile_url"]
            account.save()
        except Exception:
            celery_logger.exception(f'Error while updating tokens{Exception}')


@celery_app.task(name='avito_account.tasks.balance_alert_send_task')
def balance_alert_send_task():
    async_to_sync(balance_alert_send)()


async def balance_alert_send():
    avito_accounts = await sync_to_async(list)(AvitoAccount.objects.filter(
        created_by__is_active=True,
        telegram_id__isnull=False))
    for avito_account in avito_accounts:
        if avito_account.balance_alerting:
            # balance = await get_balance(avito_account)
            balance = avito_api.get_balance(avito_account, tlogger=TraceLogger()).real
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


@shared_task
def actualize_avito_webhooks_subscriptions(accounts_ids: list[int] | None = None) -> None:
    accounts = AvitoAccount.objects.all()
    if accounts_ids is not None:
        accounts = accounts.filter(id__in=accounts_ids)

    for account in accounts:
        update_avito_webhook_subscription(account)
