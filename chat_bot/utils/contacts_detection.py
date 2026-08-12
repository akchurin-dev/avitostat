import re

from django.db.models import Q

import messaging.api
from avito_account.models.models import AvitoAccount
from chat_bot.models import ChatBotTask
from utils.miscellaneous import find_phone_numbers_in_chat

TELEGRAM_RE = re.compile(r"(?:@[a-zA-Z][a-zA-Z0-9_]{3,}|t\.me/\S+)", re.IGNORECASE)


def has_contact_in_chat_tasks(account: AvitoAccount, chat_id: str) -> bool:
    return ChatBotTask.objects.filter(
        avito_account=account,
        chat_id=chat_id,
    ).filter(
        Q(mobile__isnull=False) & ~Q(mobile="")
        | Q(whatsapp__isnull=False) & ~Q(whatsapp="")
        | Q(telegram__isnull=False) & ~Q(telegram="")
    ).exists()


def _client_text_messages(messages: list[messaging.api.ChatMessage]) -> list[str]:
    texts: list[str] = []

    for message in messages:
        if message["direction"] != "in" or message["type"] != "text":
            continue

        text = message["content"].get("text")
        if text:
            texts.append(text)

    return texts


def has_contact_in_messages(messages: list[messaging.api.ChatMessage]) -> bool:
    client_texts = _client_text_messages(messages)

    if find_phone_numbers_in_chat(client_texts):
        return True

    return any(TELEGRAM_RE.search(text) for text in client_texts)


def chat_has_contact(
    account: AvitoAccount,
    chat_id: str,
    messages: list[messaging.api.ChatMessage] | None = None,
) -> bool:
    if has_contact_in_chat_tasks(account, chat_id):
        return True

    if messages is not None and has_contact_in_messages(messages):
        return True

    return False
