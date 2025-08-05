from avito_account.models.models import AvitoAccount
from chat_bot.models import ChatBotTask
from messaging.api import Chat
from messaging.api import ChatMessage
from utils.logging import TraceLogger


def is_message_actual(task: ChatBotTask, messages: list[ChatMessage], *, tlogger: TraceLogger) -> bool:
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
