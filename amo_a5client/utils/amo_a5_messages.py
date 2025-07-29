import amo.models
import messaging.api
from utils.logging import TraceLogger


def manager_interfere(account_id: str, lead_id: str, messages: list[messaging.api.ChatMessage]) -> bool:
    chatbot_answers = amo.models.AmoChatBotTask.objects.filter(
        account_id=account_id,
        lead_id=lead_id,
    )
    chatbot_answers_id = [task.message_id for task in chatbot_answers]
    messages_id = {msg["id"] for msg in messages if msg["direction"] == "out"}

    manager_answers_id = messages_id.difference(chatbot_answers_id)
    return len(manager_answers_id) > 0


def is_message_actual(task: amo.models.AmoChatBotTask, messages: list[messaging.api.ChatMessage], *, tlogger: TraceLogger) -> bool:
    chatbot_answers: set[str | None] = {
        t.answer_text
            for t in amo.models.AmoChatBotTask.get_tasks_by_chat(task.account, task.chat_id)
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
