from typing import Literal

from celery import shared_task
from openai.types.responses import EasyInputMessageParam
from openai.types.responses import ResponseInputItemParam

import amo.models
import sandbox_chats.models
from amo.utils.ai import answers as amo_answers
from utils.logging import TraceLogger


@shared_task
def run_sandbox_session(chatbot_id: int) -> None:
    tlogger = TraceLogger()

    chatbot = amo.models.AmoChatBot.objects.get(pk=chatbot_id)
    session = amo.models.AmoSandboxSession.instantiate(chatbot.pk)
    session.save()

    input_chats = amo.models.AmoChatbotSandboxInputChatLink.get_input_chats_by_chatbot(chatbot.pk)

    for input_chat in input_chats:
        output_chat = amo.models.AmoSandboxSessionChat.instantiate(
            session_id=session.pk,
            template_chat_id=input_chat.pk,
        )
        output_chat.save()

        input_chat_messages = sandbox_chats.models.InputChatMessage.get_messages_by_chat(input_chat.pk)
        for message in input_chat_messages:
            output_chat_message = amo.models.AmoSandboxOutputChatMessage.create_instance_from_input_chat_message(message, output_chat.pk)
            output_chat_message.save()

        handle_chat(chatbot, output_chat, list(input_chat_messages), tlogger=tlogger)

    session.finished = True
    session.save()


def handle_chat(
    chatbot: amo.models.AmoChatBot,
    output_chat: amo.models.AmoSandboxSessionChat,
    messages: list[sandbox_chats.models.BaseMessage],
    *,
    tlogger: TraceLogger,
) -> None:

    formatted_messages = _format_messages(messages, tlogger=tlogger)
    answer = amo_answers.generate_answer(
        account=chatbot.account,
        chatbot=chatbot,
        messages=formatted_messages,
        known_info={},
        from_sandbox=True,
        tlogger=tlogger,
    )

    new_message = amo.models.AmoSandboxOutputChatMessage.instantiate(
        chat_id=output_chat.pk,
        from_customer=False,
        text=answer.answer,
    )
    new_message.save()


def _format_messages(messages: list[sandbox_chats.models.BaseMessage], *, tlogger: TraceLogger) -> list[ResponseInputItemParam]:
    formatted_messages: list[ResponseInputItemParam] = []

    for message in messages:
        role: Literal["assistant", "user"] = "assistant"
        if message.from_customer:
            role = "user"

        formatted_message: EasyInputMessageParam

        if message.text:
            formatted_message = {
                "role": role,
                "content": message.text,
            }
        elif message.image_url:
            formatted_message = {
                "role": role,
                "content": [
                    {
                        "type": "input_image",
                        "image_url": message.image_url,
                        "detail": "low",
                    },
                ],
            }
        else:
            tlogger.error("Empty message")
            continue

        formatted_messages.append(formatted_message)

    return formatted_messages
