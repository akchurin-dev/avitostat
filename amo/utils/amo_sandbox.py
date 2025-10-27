from celery import shared_task

import amo.models
import sandbox_chats.models


@shared_task
def run_sandbox_session(chatbot_id: int) -> None:
    chatbot = amo.models.AmoChatBot.objects.get(pk=chatbot_id)
    session = amo.models.AmoSandboxSession.instantiate(chatbot.pk)
    session.save()

    input_chats = amo.models.AmoChatbotSandboxInputChatLink.get_input_chats_by_chatbot(chatbot.pk)

    for input_chat in input_chats:
        output_chat = amo.models.AmoSandboxSessionChat.instantiate(session.pk)
        output_chat.save()

        input_chat_messages = sandbox_chats.models.InputChatMessage.get_messages_by_chat(input_chat.pk)
        for message in input_chat_messages:
            amo.models.AmoSandboxOutputChatMessage.from_input_chat_message(message, output_chat.pk)
