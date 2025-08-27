from avito_account.models.models import AvitoAccount
from base import settings
from chat_bot.models import ChatBotTask
from chat_bot.utils import avito_api
from messaging.api import Chat
from messaging.api import ChatMessage as ChatMessageDict
from utils import httpx_helper
from utils.logging import TraceLogger


MAX_MESSAGES_ON_DEBUG = 5


def is_message_actual(task: ChatBotTask, messages: list[ChatMessageDict], *, tlogger: TraceLogger) -> bool:
    chatbot_answers: set[str | None] = {
        t.answer_text
            for t in ChatBotTask.get_tasks_by_chat(task.avito_account, task.chat_id)
    }

    for i in range(len(messages) - 1, -1, -1):
        if messages[i]["type"] == "system":
            continue

        if messages[i]["created"] < task.message_created_at.timestamp() or messages[i]["id"] == task.message_id:
            break

        if messages[i]["direction"] == "in":
            tlogger.info("Found newer incoming message")
            return False

        if messages[i]["direction"] == "out" and messages[i]["content"].get("text", "") not in chatbot_answers:
            tlogger.info("Found newer message outgoing not from bot")
            return False

    return True


def get_all_messages(account: AvitoAccount, chat_id: str, *, tlogger: TraceLogger) -> list[avito_api.ChatMessage]:
    limit = 50
    offset = 0

    all_messages: list[avito_api.ChatMessage] = []

    while True:
        messages = avito_api.get_messages_page(
            account=account,
            chat_id=chat_id,
            offset=offset,
            limit=limit,
            tlogger=tlogger,
        )

        if len(messages) == 0:
            break

        all_messages.extend(messages)

        offset += limit

    all_messages.reverse()
    all_messages = _filter_messages(all_messages)
    _print_chat(all_messages, tlogger=tlogger)

    return all_messages


def get_messages_first_page(account: AvitoAccount, chat_id: str, *, tlogger: TraceLogger) -> list[avito_api.ChatMessage]:
    messages = avito_api.get_messages_page(
        account=account,
        chat_id=chat_id,
        offset=0,
        limit=50,
        tlogger=tlogger,
    )

    messages.reverse()
    messages = _filter_messages(messages)
    _print_chat(messages, tlogger=tlogger)

    return messages


def _filter_messages(messages: list[avito_api.ChatMessage]) -> list[avito_api.ChatMessage]:
    if settings.ENVIRONMENT == "DEVELOPMENT":
        return messages[-MAX_MESSAGES_ON_DEBUG:]

    if settings.ENVIRONMENT != "TESTING":
        return messages

    url = settings.DJANGO_BASE_URL + "/deep_tests/prev-session-last-avito-message"

    response = httpx_helper.request("GET", url)
    response.raise_for_status()

    prev_session_last_message_id = response.text
    result = []

    for msg in messages[::-1]:
        if msg.id == prev_session_last_message_id:
            break

        result.append(msg)

    return result[::-1]


def _print_chat(messages: list, *, tlogger: TraceLogger):
    lines: list[str] = ["Get messages:"]

    for msg in messages:
        direction = msg["direction"]
        id = msg["id"]
        text = msg.get("content", {}).get("text")
        lines.append(f"{direction} ({id}): {text}")

    tlogger.info("\n".join(lines))
