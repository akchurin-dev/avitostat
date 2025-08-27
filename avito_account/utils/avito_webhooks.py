import amo_a5client.models
import chat_bot.models
from avito_account.models.models import AvitoAccount
from chat_bot.utils import avito_api
from utils.logging import TraceLogger


def update_avito_webhook_subscription(account: AvitoAccount) -> None:
    tlogger = TraceLogger()

    has_active_chatbots = chat_bot.models.AiChatBot.objects.filter(
        account=account,
        is_active=True,
    ).exists()

    if has_active_chatbots:
        tlogger.info(f"'{account.name}' linked with active chatbot")
        avito_api.subscribe_for_messages(account, tlogger=tlogger)
        return

    linked_with_amo = amo_a5client.models.AmoAvitoAccountsLink.objects.filter(
        avito_account=account,
        is_active=True,
    ).exists()

    if linked_with_amo:
        tlogger.info(f"'{account.name}' linked with amo accounts")
        avito_api.subscribe_for_messages(account, tlogger=tlogger)
        return

    tlogger.info(f"'{account.name}' doesn't need webhook subscription")
    avito_api.unsubscribe_from_messages(account, tlogger=tlogger)
