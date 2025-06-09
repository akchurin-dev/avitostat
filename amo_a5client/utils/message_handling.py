import datetime

from celery import shared_task

import amo.models
import messaging.api
from amo.utils import ai_answer_using
from amo.utils import amo_ai
from amo.utils import amo_messages
from amo.utils import amo_reports
from amo.utils import chatbot_lead_pair_defining
from amo_a5client.config import ORIGIN_NAME
from amo_a5client.utils import amo_a5_ai
from amo_a5client.utils import amo_a5_messages
from avito_account.models.models import AvitoAccount
from chat_bot.api.core import AvitoMessengerSync
from utils.logging import TraceLogger


def launch_new_message_handling(
    amo_account_id: int,
    avito_account_id: int,
    contact_id: int,
    lead_id: int | None,
    chat_id: str,
    message_id: str,
    message_created_at_ts: int,
    text: str,
    *,
    tlogger: TraceLogger
) -> None:

    amo_account = amo.models.AmoAccount.objects.get(pk=amo_account_id)

    chatbot_lead_pair = chatbot_lead_pair_defining.define_chatbot_and_lead(
        account=amo_account,
        contact_id=contact_id,
        advised_lead_id=lead_id,
        origin=ORIGIN_NAME,
        tlogger=tlogger,
    )

    if chatbot_lead_pair is None:
        tlogger.info("Stop handling. Chatbot and lead aren't defined")
        return

    chatbot = chatbot_lead_pair.chatbot
    lead = chatbot_lead_pair.lead

    tlogger.info(f"Selected chat bot is '{chatbot}'")
    tlogger.info(f"Selected lead id={lead.id}")

    message_created_at = datetime.datetime.fromtimestamp(message_created_at_ts, datetime.timezone.utc)

    tlogger.info((
        "New message:\n"
        f"domain: {amo_account.domain}\n"
        f"lead_id: {lead.id}\n"
        f"pipeline_id: {lead.pipeline_id}\n"
        f"status_id: {lead.status_id}\n"
        f"contact_id: {contact_id}\n"
        f"avito_chat_id: {chat_id}\n"
        f"avito_message_id: {message_id}\n"
        f"message_created_at: {message_created_at.isoformat()}\n"
        f"text: {text}"
    ))

    task, created = amo.models.AmoChatBotTask.objects.get_or_create(
        account=amo_account,
        chat_id=chat_id,
        message_id=message_id,
        defaults={
            "chatbot": chatbot,
            "lead_id": lead.id,
            "contact_id": contact_id,
            "talk_id": None,
            "message_created_at": message_created_at,
            "message_type": amo_messages.MessageTypeEnum.TEXT.value,
            "text": text,
            "file_link": "",
        }
    )

    if not created:
        tlogger.info("Stop handling. Task already created")
        return

    if task.cancel_if_not_newest(tlogger=tlogger):
        tlogger.info("Stop handling")
        return

    ok = task.cancel_others(tlogger)
    if not ok:
        tlogger.info("Stop handling. Task was canceled before it was started")
        return

    tlogger.info(f"Task ({task.pk}) created successfully")

    tlogger.info(f"Wait for {chatbot.waiting_seconds} seconds...")

    prepare_message_handling_data.s(
        task_id=task.pk,
        avito_account_id=avito_account_id,
        trace_id=tlogger.trace_id,
    ).apply_async(countdown=chatbot.waiting_seconds)


@shared_task
def prepare_message_handling_data(task_id: int, avito_account_id: int, *, trace_id: str) -> None:
    @amo.models.AmoChatBotTask.interrupt_task_if_error
    def f(avito_account_id: int, *, task_id: int, trace_id: str) -> None:
        tlogger = TraceLogger(trace_id)

        ok = amo.models.AmoChatBotTask.change_task_status(
            task_id=task_id,
            new_status=amo.models.AmoChatBotTask.Status.PREPARING_DATA,
            tlogger=tlogger,
        )
        if not ok:
            tlogger.info("Stop handling. Can't go to data preparing")
            return

        task = amo.models.AmoChatBotTask.objects.get(pk=task_id)
        avito_account = AvitoAccount.objects.get(pk=avito_account_id)
        chat = messaging.api.MessagingAPISync.get_chat_last_50_messages_by_chat_id(avito_account, task.chat_id, trace_id=trace_id)
        messages = chat.get("messages", [])

        last_message = messages[-1]

        if last_message["type"] == "system":
            last_message = messages[-2]

        if last_message["id"] != task.message_id:
            task.cancel(tlogger=tlogger)
            tlogger.info(f"Stop handling. Message (id='{task.message_id}') is not actual")
            return

        if last_message["direction"] != "in":
            task.cancel(tlogger=tlogger)
            tlogger.info(f"Stop handling. Message (id='{task.message_id}') is outgoing")
            return

        manager_interfere = amo_a5_messages.manager_interfere(task.account.pk, task.lead_id, messages)
        assert task.chatbot
        if manager_interfere and task.chatbot.shutdown_after_manager:
            task.cancel(tlogger=tlogger)
            tlogger.info("Stop handling. Shutdown after manager")
            return

        generate_ai_answer.delay(
            task_id=task_id,
            messages=messages,
            avito_account_id=avito_account_id,
            trace_id=trace_id,
        )

    f(
        avito_account_id=avito_account_id,
        task_id=task_id,
        trace_id=trace_id,
    )


@shared_task
def generate_ai_answer(task_id: int, messages: list[messaging.api.ChatMessage], avito_account_id: int, *, trace_id: str) -> None:
    @amo.models.AmoChatBotTask.interrupt_task_if_error
    def f(messages: list[messaging.api.ChatMessage], *, task_id: int, trace_id: str) -> None:
        tlogger = TraceLogger(trace_id)

        task = amo.models.AmoChatBotTask.objects.get(pk=task_id)
        assert task.chatbot

        ok = task.change_status(task.Status.ANSWER_GENERATION, tlogger=tlogger)
        if not ok:
            tlogger.info("Stop handling. Can't go to answer generation")
            return

        # transctiptions = amo_transcriptions.get_transcriptions_for_voice_messages(task.account, messages, tlogger=tlogger)

        ai_answer = amo_a5_ai.generate_answer(
            chatbot=task.chatbot,
            messages=messages,
            amo_account=task.account,
            lead_id=int(task.lead_id),
            tlogger=tlogger,
        )

        assert ai_answer.payload.answer
        ai_answer.payload.answer = task.chatbot.message_prefix + ai_answer.payload.answer + task.chatbot.message_postfix

        tlogger.info({"ai_answer": ai_answer.model_dump()})

        finish_handling.delay(
            task_id=task_id,
            avito_account_id=avito_account_id,
            ai_answer_serializable=ai_answer.model_dump(),
            trace_id=trace_id,
        )

    f(
        messages=messages,
        task_id=task_id,
        trace_id=trace_id,
    )


@shared_task
def finish_handling(task_id: int, avito_account_id: int, ai_answer_serializable, *, trace_id: str) -> None:
    @amo.models.AmoChatBotTask.interrupt_task_if_error
    def f(ai_answer: amo_ai.AIAnswer, avito_account_id: int, *, task_id: int, trace_id: str) -> None:
        tlogger = TraceLogger(trace_id)

        task = amo.models.AmoChatBotTask.objects.get(pk=task_id)

        ok = task.change_status(task.Status.ANSWER_SENDING, tlogger=tlogger)
        if not ok:
            tlogger.info("Stop handling. Can't go to answer sending")
            return

        assert task.chatbot

        ai_answer_using.update_lead_and_contact(
            account=task.account,
            ai_answer=ai_answer,
            lead_id=int(task.lead_id),
            contact_id=int(task.contact_id),
            tlogger=tlogger,
        )

        status_change_result = ai_answer_using.change_lead_status(
            chatbot=task.chatbot,
            ai_answer=ai_answer,
            lead_id=int(task.lead_id),
            contact_id=int(task.contact_id),
            tlogger=tlogger,
        )

        assert ai_answer.payload.answer

        message = ai_answer.payload.answer
        if status_change_result.status_changed_on_qualification and task.chatbot.message_when_qualification:
            message = task.chatbot.message_when_qualification

        avito_account = AvitoAccount.objects.get(pk=avito_account_id)

        AvitoMessengerSync.send_message_to_avito(avito_account, avito_account.pk, task.chat_id, message)

        amo.models.AmoChatBotTask.save_ai_result(
            pk=task.pk,
            answer_text=ai_answer.payload.answer,
            tokens_completion=ai_answer.tokens_completion,
            tokens_prompt=ai_answer.tokens_prompt,
        )

        task.change_status(task.Status.FINISHED, tlogger=tlogger)

    ai_answer = amo_ai.AIAnswer.model_validate(ai_answer_serializable)

    f(ai_answer, avito_account_id, task_id=task_id, trace_id=trace_id)
