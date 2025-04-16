import datetime

import amo.models
import amo.tasks
from amo.utils import amo_chatbots
from amo.utils import amo_chatbottasks
from base import settings
from utils.logging import TraceLogger


def launch_handler(
    account_id: int,
    lead_id: int | None,
    contact_id: str,
    origin: str,
    chat_id: str,
    talk_id: int,
    message_id: str,
    message_created_at: datetime.datetime,
    text: str,
    *,
    trace_id: str,
) -> None:

    tlogger = TraceLogger(trace_id)

    tlogger.info((
        "New message:\n"
        f"account_id: {account_id}\n"
        f"lead_id: {lead_id}\n"
        f"contact_id: {contact_id}\n"
        f"origin: {origin}\n"
        f"chat_id: {chat_id}\n"
        f"talk_id: {talk_id}\n"
        f"message_id: {message_id}\n"
        f"message_created_at: {message_created_at.isoformat()}\n"
        f"text: {text}"
    ))

    if lead_id is None:
        tlogger.info("Stop handling. lead_id is null")
        return

    amo.models.AmoTalkLeadLink.objects.get_or_create(
        account_id=account_id,
        talk_id=talk_id,
        lead_id=lead_id,
    )

    chatbot = amo_chatbots.define_chatbot(account_id, lead_id, origin, tlogger=tlogger)

    if chatbot is None:
        tlogger.info("Stop handling. Available chat bots wasn't found")
        return

    tlogger.info(f"Selected chat bot is {chatbot}")

    task, created = amo.models.AmoChatBotTask.objects.get_or_create(
        account_id=account_id,
        chat_id=chat_id,
        message_id=message_id,
        defaults={
            "chatbot": chatbot,
            "lead_id": lead_id,
            "contact_id": contact_id,
            "talk_id": talk_id,
            "message_created_at": message_created_at,
            "text": text,
        },
    )
    if not created:
        tlogger.info("Stop handling. Task exists already")
        return

    newer_tasks = amo.models.AmoChatBotTask.objects.filter(
        message_created_at__gt=task.message_created_at,
        object_id=amo_chatbottasks.get_object_id(
            domain=task.account.domain,
            chat_id=task.chat_id,
        ),
    )

    if newer_tasks.exists():
        tlogger.info("Stop handling. There is task with newer message")
        task.cancel(tlogger)
        return

    ok = task.cancel_others(tlogger=tlogger)
    if not ok:
        tlogger.info("Stop handling. Task was canceled before it was started")
        return

    tlogger.info(f"Task ({task.pk}) created successfully")

    wait_sec = chatbot.waiting_minutes * 60
    wait_sec /= 60 # TODO only while amo is being tested

    if settings.ENVIRONMENT == "DEVELOPMENT":
        wait_sec = 5

    if settings.ENVIRONMENT == "TESTING":
        wait_sec = 5

    tlogger.info(f"Wait for {wait_sec} seconds...")

    amo.tasks.prepare_message_handling_data.s(task_id=task.pk, trace_id=tlogger.trace_id).apply_async(countdown=wait_sec)
