import datetime

from celery import shared_task

import amo.models
import messaging.api
from amo.utils import ai_answer_using
from amo.utils import amo_api
from amo.utils import amo_fields
from amo.utils import amo_leads
from amo.utils import amo_messages
from amo.utils import chatbot_lead_pair_defining
from amo.utils.message_handling import additional_values_finding
from amo.utils.ai import answers
from amo.utils.ai import fields_recognition
# from amo.utils.ai import isolated_check
from amo_a5client.config import ORIGIN_NAME
# from amo_a5client.utils import amo_a5_ai
from amo_a5client.utils import amo_a5_messages
from avito_account.models.models import AvitoAccount
from chat_bot.api.core import AvitoMessengerSync
from chat_bot.utils import avito_transcriptions
from chat_bot.utils.messages_formating import avito_chat_to_gpt_format
from utils.logging import TraceLogger


@shared_task
def launch_new_message_handling(
    amo_account_id: int,
    avito_account_id: int,
    contact_id: int,
    lead_id: int | None,
    chat_id: str,
    message_id: str,
    message_created_at_ts: int,
    text: str,
    time_left_for_retries_sec: float = 0,
    *,
    trace_id: str,
) -> None:

    tlogger = TraceLogger(trace_id)

    amo_account = amo.models.AmoAccount.objects.get(pk=amo_account_id)

    chatbot_lead_pair = chatbot_lead_pair_defining.define_chatbot_and_lead(
        account=amo_account,
        contact_id=contact_id,
        advised_lead_id=lead_id,
        origin=ORIGIN_NAME,
        tlogger=tlogger,
    )

    if chatbot_lead_pair is None:
        if time_left_for_retries_sec < 5:
            launch_new_message_handling.s(
                amo_account_id=amo_account_id,
                avito_account_id=avito_account_id,
                contact_id=contact_id,
                lead_id=lead_id,
                chat_id=chat_id,
                message_id=message_id,
                message_created_at_ts=message_created_at_ts,
                text=text,
                time_left_for_retries_sec=100,
                trace_id=tlogger.trace_id,
            ).apply_async(countdown=60 * 3)

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
        tlogger.info("Stop handling. Task is not newest")
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
        messages = chat.get("messages", [])[-10:]

        if not amo_a5_messages.is_message_actual(task, messages, tlogger=tlogger):
            task.cancel(tlogger=tlogger)
            tlogger.info(f"Stop handling. Message (id='{task.message_id}') is not actual")
            return

        incoming = False
        for i in range(len(messages) - 1, -1, -1):
            if messages[i]["id"] == task.message_id:
                incoming = messages[i]["direction"] == "in"
                break

        if not incoming:
            task.cancel(tlogger=tlogger)
            tlogger.info(f"Stop handling. Message (id='{task.message_id}') is outgoing")
            return

        manager_interfere = amo_a5_messages.manager_interfere(task.account.pk, task.lead_id, messages)
        assert task.chatbot
        if manager_interfere and task.chatbot.shutdown_after_manager:
            task.cancel(tlogger=tlogger)
            tlogger.info("Stop handling. Shutdown after manager")
            return

        lead = amo_api.get_lead(task.account, task.lead_id, tlogger=tlogger)
        contact = amo_leads.get_lead_contact(task.account, lead, tlogger=tlogger)
        assert contact

        known_info = amo_fields.get_filled_fillable_fields(task.chatbot, lead, contact)
        tlogger.info({"Known info": known_info})

        generate_ai_answer.delay(
        # generate_ai_answer(
            task_id=task_id,
            messages=messages,
            avito_account_id=avito_account_id,
            known_info=known_info,
            trace_id=trace_id,
        )

    f(
        avito_account_id=avito_account_id,
        task_id=task_id,
        trace_id=trace_id,
    )


@shared_task
def generate_ai_answer(
    task_id: int,
    messages: list[messaging.api.ChatMessage],
    avito_account_id: int,
    known_info: dict[str, list[str]],
    *,
    trace_id: str,
) -> None:

    @amo.models.AmoChatBotTask.interrupt_task_if_error
    def f(messages: list[messaging.api.ChatMessage], *, task_id: int, trace_id: str) -> None:
        tlogger = TraceLogger(trace_id)

        task = amo.models.AmoChatBotTask.objects.get(pk=task_id)
        assert task.chatbot

        ok = task.change_status(task.Status.ANSWER_GENERATION, tlogger=tlogger)
        if not ok:
            tlogger.info("Stop handling. Can't go to answer generation")
            return

        transcriptions = avito_transcriptions.get_voice_messages_transcriptions(
            avito_account=AvitoAccount.objects.get(pk=avito_account_id),
            chat={"id": task.chat_id, "messages": messages},
            tlogger=tlogger,
        )
        messages_ai_format = avito_chat_to_gpt_format(messages, transcriptions)

        answer, tokens_prompt1, tokens_completion1 = answers.generate_answer(
            account=task.account,
            chatbot=task.chatbot,
            messages=messages_ai_format,
            # lead_id=int(task.lead_id),
            known_info=known_info,
            tlogger=tlogger,
        )

        # tlogger.info({"ai_answer": ai_answer.model_dump()})

        fillable_fields = list(amo.models.FillableField.objects.filter(chatbot=task.chatbot))
        entities_fields_values, tokens_prompt2, tokens_completion2 = fields_recognition.recognize_fields(
            account=task.account,
            messages=messages_ai_format,
            fillable_fields=fillable_fields,
            tlogger=tlogger
        )

        additional_values_finding(entities_fields_values, messages_ai_format, tlogger=tlogger)

        finish_handling.delay(
        # finish_handling(
            task_id=task_id,
            avito_account_id=avito_account_id,
            answer=answer,
            entities_fields_values=entities_fields_values,
            tokens_prompt=tokens_prompt1 + tokens_prompt2,
            tokens_completion=tokens_completion1 + tokens_completion2,
            trace_id=trace_id,
        )

    f(
        messages=messages,
        task_id=task_id,
        trace_id=trace_id,
    )


@shared_task
def finish_handling(
    task_id: int,
    avito_account_id: int,
    answer: str,
    entities_fields_values: fields_recognition.EntitiesFieldsValues,
    tokens_prompt: int,
    tokens_completion: int,
    *,
    trace_id: str,
) -> None:
    @amo.models.AmoChatBotTask.interrupt_task_if_error
    def f(avito_account_id: int, *, task_id: int, trace_id: str) -> None:
        tlogger = TraceLogger(trace_id)

        task = amo.models.AmoChatBotTask.objects.get(pk=task_id)

        ok = task.change_status(task.Status.ANSWER_SENDING, tlogger=tlogger)
        if not ok:
            tlogger.info("Stop handling. Can't go to answer sending")
            return

        assert task.chatbot

        lead, contact = amo_leads.get_lead_contact_pair(task.account, task.lead_id, tlogger=tlogger)

        ai_answer_using.update_lead_and_contact(
            account=task.account,
            entities_fields_values=entities_fields_values,
            lead=lead,
            contact=contact,
            tlogger=tlogger,
        )

        status_change_result = ai_answer_using.change_lead_status(
            chatbot=task.chatbot,
            # ai_answer=ai_answer,
            lead=lead,
            tlogger=tlogger,
        )

        message = answer
        if status_change_result.status_changed_on_qualification and task.chatbot.message_when_qualification:
            message = task.chatbot.message_when_qualification

        avito_account = AvitoAccount.objects.get(pk=avito_account_id)

        AvitoMessengerSync.send_message_to_avito(avito_account, task.chat_id, message)

        if status_change_result.status_changed_on_qualification:
            task.qualification_achieved = True
            task.save()

        amo.models.AmoChatBotTask.save_ai_result(
            pk=task.pk,
            answer_text=answer,
            tokens_completion=tokens_completion,
            tokens_prompt=tokens_prompt,
        )

        task.change_status(task.Status.FINISHED, tlogger=tlogger)

    f(avito_account_id, task_id=task_id, trace_id=trace_id)
