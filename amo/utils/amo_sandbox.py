from celery import shared_task

import amo.models
import sandbox_chats.models
from amo.utils.ai import answer_evaluation
from amo.utils.ai import answers as amo_answers
from utils import universal_messages
from utils.logging import TraceLogger


REPEATS_PER_CHAT = 3


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

        handle_chat(
            chatbot=chatbot,
            input_chat=input_chat,
            output_chat=output_chat,
            messages=[message.as_universal_format() for message in input_chat_messages],
            tlogger=tlogger,
        )

    session.finished = True
    session.save()


def handle_chat(
    chatbot: amo.models.AmoChatBot,
    input_chat: sandbox_chats.models.InputChat,
    output_chat: amo.models.AmoSandboxSessionChat,
    messages: list[universal_messages.Message],
    *,
    tlogger: TraceLogger,
) -> None:

    for _ in range(REPEATS_PER_CHAT):
        answer = amo_answers.generate_answer(
            account=chatbot.account,
            chatbot=chatbot,
            messages=[message.as_openai_format() for message in messages],
            known_info={},
            from_sandbox=True,
            tlogger=tlogger,
        )

        evaluation = answer_evaluation.evaluate_answer(
            account=chatbot.account,
            messages=messages,
            requirements=input_chat.answer_requirements,
            tlogger=tlogger,
        )

        new_answer = amo.models.AmoSandboxAnswer.instantiate(
            chat_id=output_chat.pk,
            text=answer.answer,
            rate=evaluation.rate,
            rate_explanation=evaluation.explanation,
        )
        new_answer.save()
