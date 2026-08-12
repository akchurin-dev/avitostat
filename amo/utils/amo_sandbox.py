import statistics
from typing import Iterable

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
    input_chats = amo.models.AmoChatbotSandboxInputChatLink.get_input_chats_by_chatbot(chatbot.pk)
    session = _create_sandbox_session(chatbot, input_chats)

    session.mark_as_inprogress(save=True)

    try:
        for input_chat in input_chats:
            output_chat, messages = _create_output_chat_with_messages(session.pk, input_chat)
            handle_chat(
                chatbot=chatbot,
                output_chat=output_chat,
                messages=[message.as_universal_format() for message in messages],
                tlogger=tlogger,
            )
    except:
        session.mark_as_interrupted(save=True)
        raise
    else:
        session.mark_as_finished(save=True)


def handle_chat(
    chatbot: amo.models.AmoChatBot,
    output_chat: sandbox_chats.models.SandboxOutputChat,
    messages: list[universal_messages.Message],
    *,
    tlogger: TraceLogger,
) -> None:

    answers: list[sandbox_chats.models.SandboxTextAnswer] = []
    rates: list[int] = []

    for _ in range(REPEATS_PER_CHAT):
        answer = amo_answers.generate_answer(
            account=chatbot.account,
            chatbot=chatbot,
            messages=[message.as_openai_format() for message in messages],
            known_info={},
            from_sandbox=True,
            tlogger=tlogger,
        )

        new_message = universal_messages.Message(author="manager", text=answer.answer, image_url=None)

        evaluation = answer_evaluation.evaluate_answer(
            account=chatbot.account,
            messages=messages + [new_message],
            requirements=output_chat.answer_requirements,
            tlogger=tlogger,
        )

        new_answer = sandbox_chats.models.SandboxTextAnswer.instantiate(
            chat_id=output_chat.pk,
            text=answer.answer,
            rate=evaluation.rate,
            rate_explanation=evaluation.explanation,
        )

        answers.append(new_answer)
        rates.append(evaluation.rate)

    sandbox_chats.models.SandboxTextAnswer.objects.bulk_create(answers)

    output_chat.avg_rate = round(statistics.mean(rates), 2)
    output_chat.min_rate = min(rates)
    output_chat.max_rate = max(rates)
    output_chat.save()


def _create_sandbox_session(
    chatbot: amo.models.AmoChatBot,
    input_chats: Iterable[sandbox_chats.models.SandboxInputChat],
) -> sandbox_chats.models.SandboxSession:

    session = sandbox_chats.models.SandboxSession.objects.create()

    chatbot_session_link = amo.models.AmoChatbotSandboxSessionLink.instantiate(chatbot.pk, session.pk)
    chatbot_session_link.save()

    chat_session_links = [sandbox_chats.models.SandboxSessionInputChatLink.instantiate(session.pk, chat.pk) for chat in input_chats]
    sandbox_chats.models.SandboxSessionInputChatLink.objects.bulk_create(chat_session_links)

    return session


def _create_output_chat_with_messages(
    session_id: int,
    input_chat: sandbox_chats.models.SandboxInputChat,
) -> tuple[sandbox_chats.models.SandboxOutputChat, list[sandbox_chats.models.ChatMessage]]:

    output_chat = sandbox_chats.models.SandboxOutputChat.instantiate(session_id, input_chat)
    output_chat.save()

    input_chat_messages = sandbox_chats.models.ChatMessage.get_messages_by_input_chat(input_chat.pk)
    output_chat_messages: list[sandbox_chats.models.ChatMessage] = []

    for message in input_chat_messages:
        output_chat_message = message.copy_without_chat_id()
        output_chat_message.output_chat = output_chat
        output_chat_messages.append(output_chat_message)

    sandbox_chats.models.ChatMessage.objects.bulk_create(output_chat_messages)

    return output_chat, output_chat_messages
