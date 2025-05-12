from typing import Iterable

from openai.types.responses.response_text_config_param import ResponseTextConfigParam

import chat_bot.ai_utils
import chat_bot.models
import messaging.api
from utils.logging import TraceLogger


def define_chatbot(
    account: chat_bot.models.AvitoAccount,
    chat: messaging.api.Chat,
    *,
    tlogger: TraceLogger,
) -> chat_bot.models.AiChatBot | None:

    available_chatbots = chat_bot.models.AiChatBot.get_available_chatbots().filter(account=account)

    if len(available_chatbots) == 0:
        tlogger.info("Available chatbots not found")
        return None

    if len(available_chatbots) == 1:
        chatbot = available_chatbots.first()
        tlogger.info(f"Found only one available chatbot '{chatbot}'")
        return chatbot

    tlogger.info(f"Available chatbots: {[chatbot.name for chatbot in available_chatbots]}")

    prompt = _get_prompt(available_chatbots, chat)
    response_format = _get_ai_response_format(available_chatbots)

    response = chat_bot.ai_utils.client.responses.create(
        model=chat_bot.ai_utils.MODEL,
        input=[{"role": "user", "content": prompt}],
        text=response_format,
    )

    chatbot_name = response.output_text
    tlogger.info(f"Suitable chatbot name is '{chatbot_name}'")

    return available_chatbots.get(name=chatbot_name)


def _get_prompt(chatbots: Iterable[chat_bot.models.AiChatBot], chat: messaging.api.Chat) -> str:
    paragraphs: list[str] = [
        "Твоя задача определить ИИ-агента, который больше всего подходит для генерации ответа клиенту",
    ]

    messages = ["Чат с клиентом:"]

    for message in chat.get("messages", []):
        text = message["content"]["text"]
        role = "Manager"

        if message["direction"] == "in":
            role = "Client"

        messages.append(f"{role}: {text}")

    paragraphs.append("\n".join(messages))

    chatbots_description = ["Далее перечислены доступные ИИ-агенты"]

    for chatbot in chatbots:
        when_use = chatbot.description or "-"
        chatbots_description.append(f"Имя: {chatbot.name}\nКогда используется: {when_use}")

    paragraphs.append("\n\n".join(chatbots_description))

    return "\n\n\n".join(paragraphs)


def _get_ai_response_format(chatbots: Iterable[chat_bot.models.AiChatBot]) -> ResponseTextConfigParam:
    return {
        "format": {
            "type": "json_schema",
            "name": "AI defining",
            "schema": {
                "type": "string",
                "description": "Name of suitable ai-agent",
                "enum": [chatbot.name for chatbot in chatbots],
            },
        },
    }
