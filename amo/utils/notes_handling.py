import json

import amo.models
from amo.utils import amo_ai
from amo.utils import amo_api
from amo.utils import ai_answer_using
from amo.utils import chatbot_lead_pair_defining
from utils.logging import TraceLogger


def handle_new_lead_note_webhook(request_data: dict, *, tlogger: TraceLogger) -> None:
    try:
        account_id = int(request_data["account[id]"])
        note: dict = request_data["leads[note][0][note]"]

        assert note["element_type"] == "2"
        lead_id = int(note["element_id"])

        note_type = int(note["note_type"])
        text = note["text"]

        metadata: dict = json.loads(note["metadata"])
        author_name = metadata["event_source"]["author_name"]
    except:
        tlogger.info("Error when parsing amo new lead note webhook request data")
        tlogger.info(request_data)
        raise

    launch_lead_note_handling(
        account_id=account_id,
        lead_id=lead_id,
        note_type=note_type,
        author_name=author_name,
        text=text,
        tlogger=tlogger,
    )


def launch_lead_note_handling(
    account_id: int,
    lead_id: int,
    note_type: int,
    author_name: str,
    text: str,
    *,
    tlogger: TraceLogger,
) -> None:

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

    ai_answer_using.handle_ai_answer(
        chatbot=chatbot,
        ai_answer=ai_answer,
        lead_id=lead_id,
        contact_id=contact_id,
        tlogger=tlogger,
    )
