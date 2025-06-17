import json

from celery import shared_task

import amo.models
from amo.utils import ai_answer_using
from amo.utils import amo_ai
from amo.utils import amo_api
from amo.utils import amo_leads
from amo.utils import amo_messages
from amo.utils import chatbot_lead_pair_defining
from amo.utils import qualification
from utils.logging import TraceLogger


def handle_new_lead_note_webhook(request_data: dict, *, tlogger: TraceLogger) -> None:
    try:
        account_id = int(request_data["account[id]"])

        assert request_data["leads[note][0][note][element_type]"] == "2"
        lead_id = int(request_data["leads[note][0][note][element_id]"])

        note_type = int(request_data["leads[note][0][note][note_type]"])
        text = request_data["leads[note][0][note][text]"]

        metadata: dict = json.loads(request_data["leads[note][0][note][metadata]"])
        author_name = metadata["event_source"]["author_name"]
    except:
        tlogger.info("Error when parsing amo new lead note webhook request data")
        tlogger.info(request_data)
        raise

    handle_lead_note.s(
        account_id=account_id,
        lead_id=lead_id,
        note_type=note_type,
        author_name=author_name,
        text=text,
        trace_id=tlogger.trace_id,
    ).apply_async(countdown=30)


@shared_task
def handle_lead_note(
    account_id: int,
    lead_id: int,
    note_type: int,
    author_name: str,
    text: str,
    *,
    trace_id: str,
) -> None:

    tlogger = TraceLogger(trace_id)

    if note_type != 4:
        tlogger.info("Stop handling. Handle only notes with note_type = 4")
        return

    account = amo.models.AmoAccount.objects.get(amo_id=account_id)

    advised_lead = amo_api.get_lead(account, lead_id, tlogger=tlogger)
    assert advised_lead.contacts_ids
    contact_id = advised_lead.contacts_ids[0]

    chatbot_lead_pair = chatbot_lead_pair_defining.define_chatbot_and_lead(
        account=account,
        contact_id=contact_id,
        advised_lead_id=lead_id,
        note_author_name=author_name,
        tlogger=tlogger,
    )

    if chatbot_lead_pair is None:
        tlogger.info("Stop handling. Chatbot and lead aren't defined")
        return

    chatbot = chatbot_lead_pair.chatbot
    lead = chatbot_lead_pair.lead

    tlogger.info({
        "domain": account.domain,
        "chatbot": str(chatbot),
        "lead_id": lead.id,
        "pipeline_id": lead.pipeline_id,
        "status_id": lead.status_id,
        "contact_id": contact_id,
        "note_author_name": author_name,
        "text": text,
    })

    ai_answer = amo_ai.parse_form(chatbot, text, tlogger=tlogger)

    assert lead.contacts_ids is not None
    contact = amo_api.get_contact(
        account=account,
        contact_id=lead.contacts_ids[0],
        with_leads=False,
        tlogger=tlogger,
    )

    ai_answer_using.update_lead_and_contact(
        account=account,
        ai_answer=ai_answer,
        lead=lead,
        contact=contact,
        tlogger=tlogger,
    )

    if not chatbot.message_when_note_received:
        tlogger.info("Don't send message. Message when note received is blank")
        return

    chat_id = amo_messages.create_chat_and_talk(account, contact, tlogger=tlogger)
    amo_api.send_message(
        account=account,
        chat_id=chat_id,
        text=chatbot.message_when_note_received,
        tlogger=tlogger,
    )

    change_status_if_message_delivered.s(
        chatbot_id=chatbot.pk,
        lead_id=lead.id,
        trace_id=tlogger.trace_id,
    ).apply_async(countdown=30)


@shared_task
def change_status_if_message_delivered(
    chatbot_id: int,
    lead_id: int,
    *,
    trace_id: str,
) -> None:

    tlogger = TraceLogger(trace_id)

    chatbot = amo.models.AmoChatBot.objects.get(pk=chatbot_id)
    # chat = amo_messages.get_lead_chat(chatbot.account, lead_id, tlogger=tlogger)

    # if len(chat.messages) == 0:
    #     tlogger.info("Message isn't sent")
    #     return

    # if chatbot.message_when_note_received not in [msg.text for msg in chat.messages]:
    #     tlogger.info("Message when note received not found")
    #     return

    lead, contact = amo_leads.get_lead_contact_pair(chatbot.account, lead_id, tlogger=tlogger)
    qualification.change_status_if_qualification(chatbot, lead.id, tlogger=tlogger)
