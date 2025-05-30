from __future__ import annotations

import amo_a5client.models
import chat_bot.models
import chat_bot.api.subscriptions
from avito_account.models.models import AvitoAccount
from utils.logging import TraceLogger


def update_avito_webhook_subscription(account: AvitoAccount) -> None:
    tlogger = TraceLogger()

    has_active_chatbots = chat_bot.models.AiChatBot.objects.filter(
        account=account,
        is_active=True,
    ).exists()

    if has_active_chatbots:
        tlogger.info(f"'{account.name}' linked with active chatbot")
        chat_bot.api.subscriptions.subscribe_for_messages(account, raise_error=False, tlogger=tlogger)
        return

    linked_with_amo = amo_a5client.models.AmoAvitoAccountsLink.objects.filter(
        avito_account=account,
        is_active=True,
    ).exists()

    if linked_with_amo:
        tlogger.info(f"'{account.name}' linked with amo accounts")
        chat_bot.api.subscriptions.subscribe_for_messages(account, raise_error=False, tlogger=tlogger)
        return

    tlogger.info(f"'{account.name}' doesn't need webhook subscription")
    chat_bot.api.subscriptions.unsubscribe_from_messages(account, raise_error=False, tlogger=tlogger)
