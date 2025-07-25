import datetime

from celery import shared_task

import amo.models
from amo_a5client import amo_a5client
from amo.utils import amo_api
from amo.utils import amo_leads
from amo.utils import amo_messages
from amo.utils import amo_reports
from amo.utils import amo_transcriptions
from amo.utils import ai_answer_using
from amo.utils import chatbot_lead_pair_defining
from amo.utils.ai import answers
from amo.utils.ai import fields_recognition
# from amo.utils.ai import isolated_check
from utils import increasing_delay
from utils.logging import TraceLogger


RETRY_MESSAGE_HANGLING_DELAY_CONFIG = increasing_delay.IncreasingDelayConfig(
    first_delay=datetime.timedelta(seconds=10),
    multiplier=2,
    timeout=datetime.timedelta(seconds=30),
)


def handle_new_message_webhook(request_data: dict, *, tlogger: TraceLogger) -> None:
    try:
        account_id: int = int(request_data["account[id]"])
        contact_id = int(request_data["message[add][0][contact_id]"])
        origin = request_data["message[add][0][origin]"]
        chat_id: str = request_data["message[add][0][chat_id]"]
        talk_id: int = int(request_data["message[add][0][talk_id]"])
        message_id: str = request_data["message[add][0][id]"]
        text: str = request_data["message[add][0][text]"]
        message_created_at_timestamp: int = int(request_data["message[add][0][created_at]"])

        entity_type: str | None = request_data.get("message[add][0][entity_type]")
        lead_id: int | None = None
        if entity_type == "lead":
            lead_id = int(request_data["message[add][0][entity_id]"])

        attachment_type: str | None = request_data.get("message[add][0][attachment][type]")
        file_link: str | None = None
        if attachment_type:
            file_link = request_data.get("message[add][0][attachment][link]")
    except:
        tlogger.info({"Error when parse amo new message webhook request data": dict(request_data)})
        raise

    if origin == amo_a5client.config.ORIGIN_NAME:
        tlogger.info("Handle Amo as a5client")
        amo_a5client.handle_message_from_amo(
            amo_account_id=account_id,
            contact_id=contact_id,
            lead_id=lead_id,
            message_created_at_timestamp=message_created_at_timestamp,
            text=text,
            attachment_type=attachment_type,
            tlogger=tlogger,
        )
        return

    wait_sec = 0
    tlogger.info(f"Wait for {wait_sec} sec")

    launch_new_message_handling.s(
        account_id=account_id,
        contact_id=contact_id,
        lead_id=lead_id,
        origin=origin,
        chat_id=chat_id,
        talk_id=talk_id,
        message_id=message_id,
        message_created_at_timestamp=message_created_at_timestamp,
        text=text,
        file_type=attachment_type,
        file_link=file_link,
        trace_id=tlogger.trace_id,
    ).apply_async(countdown=wait_sec)


@shared_task
def launch_new_message_handling(
    account_id: int,
    contact_id: int,
    lead_id: int | None,
    origin: str,
    chat_id: str,
    talk_id: int,
    message_id: str,
    message_created_at_timestamp: int,
    text: str,
    file_type: str | None,
    file_link: str | None,
    time_left_for_retries_sec: float = 0,
    *,
    trace_id: str,
) -> None:

    tlogger = TraceLogger(trace_id)

    message_type = amo_messages.define_message_type(text, file_type)
    if message_type is None:
        tlogger.info({
            "Title": "Stop handling. Unknown message type",
            "message_text": text,
            "attachment_type": file_type,
        })
        return

    account = amo.models.AmoAccount.objects.get(pk=account_id)

    chatbot_lead_pair = chatbot_lead_pair_defining.define_chatbot_and_lead(
        account=account,
        contact_id=contact_id,
        advised_lead_id=lead_id,
        origin=origin,
        tlogger=tlogger,
    )

    if chatbot_lead_pair is None:
        if time_left_for_retries_sec < 1:
            launch_new_message_handling.s(
                account_id=account_id,
                contact_id=contact_id,
                lead_id=lead_id,
                origin=origin,
                chat_id=chat_id,
                talk_id=talk_id,
                message_id=message_id,
                message_created_at_timestamp=message_created_at_timestamp,
                text=text,
                file_type=file_type,
                file_link=file_link,
                time_left_for_retries_sec=100,
                trace_id=tlogger.trace_id,
            ).apply_async(countdown=60 * 3)

        return

    chatbot = chatbot_lead_pair.chatbot
    lead = chatbot_lead_pair.lead

    tlogger.info(f"Selected chat bot is '{chatbot}'")
    tlogger.info(f"Selected lead id={lead.id}")

    message_created_at = datetime.datetime.fromtimestamp(message_created_at_timestamp, datetime.timezone.utc)

    tlogger.info((
        "New message:\n"
        f"domain: {account.domain}\n"
        f"lead_id: {lead.id}\n"
        f"pipeline_id: {lead.pipeline_id}\n"
        f"status_id: {lead.status_id}\n"
        f"contact_id: {contact_id}\n"
        f"origin: {origin}\n"
        f"chat_id: {chat_id}\n"
        f"talk_id: {talk_id}\n"
        f"message_id: {message_id}\n"
        f"message_created_at: {message_created_at.isoformat()}\n"
        f"text: {text}"
    ))

    amo.models.AmoTalkLeadLink.objects.get_or_create(
        account_id=account_id,
        talk_id=talk_id,
        lead_id=lead.id,
    )

    task, created = amo.models.AmoChatBotTask.objects.get_or_create(
        account_id=account_id,
        chat_id=chat_id,
        message_id=message_id,
        defaults={
            "chatbot": chatbot,
            "lead_id": str(lead.id),
            "talk_id": talk_id,
            "message_created_at": message_created_at,
            "message_type": message_type.value,
            "text": text,
            "file_link": file_link or "",
        },
    )
    if not created:
        tlogger.info("Stop handling. Task exists already")
        return

    if task.cancel_if_not_newest(tlogger=tlogger):
        tlogger.info("Stop handling")
        return

    ok = task.cancel_others(tlogger=tlogger)
    if not ok:
        tlogger.info("Stop handling. Task was canceled before it was started")
        return

    tlogger.info(f"Task ({task.pk}) created successfully")

    tlogger.info(f"Wait for {chatbot.waiting_seconds} seconds...")

    prepare_message_handling_data.s(task_id=task.pk, trace_id=tlogger.trace_id).apply_async(countdown=chatbot.waiting_seconds)


@shared_task
def prepare_message_handling_data(*, task_id: int, trace_id: str):
    @amo.models.AmoChatBotTask.interrupt_task_if_error
    def f(*, task_id: int, trace_id: str) -> None:
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
        messages, talk_opened = amo_messages.get_lead_chat(
            account=task.account,
            lead_id=int(task.lead_id),
            tlogger=tlogger,
        )

        # if not talk_opened:
        #     task.cancel(tlogger=tlogger)
        #     tlogger.info("Stop handling. Talk is closed")
        #     return

        if messages[-1].id != task.message_id:
            task.cancel(tlogger=tlogger)
            tlogger.info(f"Stop handling. Message (id='{task.message_id}') is not actual")
            return

        manager_interfere = amo_messages.manager_interfere(
            account_id=task.account.pk,
            lead_id=task.lead_id,
            messages=messages,
        )
        assert task.chatbot is not None
        if manager_interfere and task.chatbot.shutdown_after_manager:
            task.cancel(tlogger=tlogger)
            tlogger.info("Stop handling. Shutdown after manager")
            return

        generate_ai_answer.delay(
            messages_serializable=[m.model_dump(mode="json") for m in messages],
            task_id=task_id,
            trace_id=trace_id,
        )

    f(task_id=task_id, trace_id=trace_id)


@shared_task
def generate_ai_answer(messages_serializable: list[dict], task_id: int, trace_id: str):
    @amo.models.AmoChatBotTask.interrupt_task_if_error
    def f(messages: list[amo_messages.Message], *, task_id: int, trace_id: str) -> None:
        tlogger = TraceLogger(trace_id)

        task = amo.models.AmoChatBotTask.objects.get(pk=task_id)
        assert task.chatbot is not None

        ok = task.change_status(task.Status.ANSWER_GENERATION, tlogger=tlogger)
        if not ok:
            tlogger.info("Stop handling. Can't go to answer generation")
            return

        transcriptions = amo_transcriptions.get_transcriptions_for_voice_messages(task.account, messages, tlogger=tlogger)
        messages_ai_format = [answers.amo_message_to_gpt_format(message, transcriptions) for message in messages]

        # ai_answer = answers.generate_answer(
        #     chatbot=task.chatbot,
        #     messages=messages_ai_format,
        #     account=task.account,
        #     lead_id=int(task.lead_id),
        #     tlogger=tlogger,
        # )
        # assert ai_answer.payload.answer
        # ai_answer.payload.answer = task.chatbot.message_prefix + ai_answer.payload.answer + task.chatbot.message_postfix
        # additional_usage = isolated_check.check_fields_isolately_and_update_ai_result(
        #     task.account,
        #     task.chatbot,
        #     messages_ai_format,
        #     ai_answer,
        #     tlogger=tlogger,
        # )

        # tlogger.info({"ai_answer": ai_answer.model_dump()})

        answer, tokens_prompt1, tokens_completion1 = answers.generate_answer(
            account=task.account,
            chatbot=task.chatbot,
            messages=messages_ai_format,
            tlogger=tlogger,
        )

        fillable_fields = list(amo.models.FillableField.objects.filter(chatbot=task.chatbot))
        entities_fields_values, tokens_prompt2, tokens_completion2 = fields_recognition.recognize_fields(
            account=task.account,
            messages=messages_ai_format,
            fillable_fields=fillable_fields,
            tlogger=tlogger,
        )

        additional_values_finding(entities_fields_values, messages_ai_format, tlogger=tlogger)

        finish_handling.delay(
        # finish_handling(
            answer=answer,
            entities_fields_values=entities_fields_values,
            messages_serializable=messages_serializable,
            tokens_prompt=tokens_prompt1 + tokens_prompt2,
            tokens_completion=tokens_completion1 + tokens_completion2,
            task_id=task_id,
            trace_id=trace_id,
        )

    messages = [amo_messages.Message.model_validate(m) for m in messages_serializable]
    f(messages, task_id=task_id, trace_id=trace_id)


@shared_task
def finish_handling(
    answer: str,
    entities_fields_values: fields_recognition.EntitiesFieldsValues,
    messages_serializable: list[dict],
    tokens_prompt: int,
    tokens_completion: int,
    *,
    task_id: int,
    trace_id: str,
) -> None:
    @amo.models.AmoChatBotTask.interrupt_task_if_error
    def f(messages: list[amo_messages.Message], *, task_id: int, trace_id: str):
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
            lead=lead,
            tlogger=tlogger,
        )

        message = answer
        if status_change_result.status_changed_on_qualification and task.chatbot.message_when_qualification:
            message = task.chatbot.message_when_qualification

        amo_api.send_message(
            account=task.account,
            chat_id=task.chat_id,
            text=message,
            tlogger=tlogger,
        )
        tlogger.info("Message was sent successfully")

        amo.models.AmoChatBotTask.save_ai_result(
            pk=task.pk,
            answer_text=answer,
            tokens_completion=tokens_completion,
            tokens_prompt=tokens_prompt,
        )

        # if ai_answer.payload.contacts:
        #     sent_report = amo.models.AmoChatBotTask.objects.filter(
        #         account_id=task.account.pk,
        #         lead_id=task.lead_id,
        #         sent_report=True,
        #     ).exists()

        #     if not sent_report:
        #         amo_reports.send_report(
        #             account=task.account,
        #             lead=lead,
        #             contact=contact,
        #             messages=messages,
        #             tlogger=tlogger,
        #         )
        #         amo.models.AmoChatBotTask.objects.filter(pk=task.pk).update(sent_report=True)

        task.change_status(task.Status.FINISHED, tlogger=tlogger)

    messages = [amo_messages.Message.model_validate(m) for m in messages_serializable]
    f(messages, task_id=task_id, trace_id=trace_id)



from openai.types.responses import ResponseInputItemParam

def additional_values_finding(
    fields_values: fields_recognition.EntitiesFieldsValues,
    messages: list[ResponseInputItemParam],
    *,
    tlogger: TraceLogger,
) -> None:

    phone_number_field_name = "Телефон"
    diameter_field_name = "Диаметр диска"

    if fields_values["contact"]:
        phone = fields_values["contact"].get(phone_number_field_name)

        if phone is None:
            phone = _find_phone_number(messages)
            if phone:
                tlogger.info("Found phone number without ai")
                fields_values["contact"][phone_number_field_name] = phone

    if fields_values["lead"]:
        diameter = fields_values["lead"].get(diameter_field_name)
        diameters = _find_diameters(messages)

        # if diameter is not None:
        #     if not diameters in 

        if diameter is None:
            if diameter:
                tlogger.info("Found diameter without ai")
                fields_values["lead"][diameter_field_name] = diameters[0]


import re
PHONE_RE = re.compile(r"\+?[78]?\s*-?\s*\(?\s*9\s*\d\s*\d\s*\)?\s*-?\s*\d\s*\d\s*\d\s*-?\s*\d\s*\d\s*-?\s*\d\s*\d")
DIAMETER_RE = re.compile(r"[rRрР][12]\d")


def _find_phone_number(messages: list[ResponseInputItemParam]) -> str | None:
    for i in range(len(messages) - 1, -1, -1):
        message = messages[i]

        if "role" not in message or message["role"] != "user":
            continue

        text = message.get("content")
        if not isinstance(text, str):
            continue

        phone = PHONE_RE.search(text)
        if phone:
            return phone.group()

    return None


def _find_diameters(messages: list[ResponseInputItemParam]) -> list[str]:
    diameters: list[str] = []

    for i in range(len(messages) - 1, -1, -1):
        message = messages[i]

        if "role" not in message or message["role"] != "user":
            continue

        text = message.get("content")
        if not isinstance(text, str):
            continue

        diameter = DIAMETER_RE.search(text)
        if diameter:
            diameters.append(diameter.group().strip("RrРр "))

    return diameters
