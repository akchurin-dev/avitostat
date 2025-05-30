import amo.models
import messaging.api


def manager_interfere(account_id: str, lead_id: str, messages: list[messaging.api.ChatMessage]) -> bool:
    chatbot_answers = amo.models.AmoChatBotTask.objects.filter(
        account_id=account_id,
        lead_id=lead_id,
    )
    chatbot_answers_id = [task.message_id for task in chatbot_answers]
    messages_id = {msg["id"] for msg in messages if msg["direction"] == "out"}

    manager_answers_id = messages_id.difference(chatbot_answers_id)
    return len(manager_answers_id) > 0
