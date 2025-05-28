from typing import NamedTuple

import amo.models
from amo.utils import amo_ai
from amo.utils import amo_api
from amo.utils import amo_fields
from amo.utils import amo_leads
from amo.utils import amo_messages
from amo.utils import amo_pipelines
from amo.utils import amo_reports
from amo.utils import qualification
from utils.logging import TraceLogger


class AnswerHandlingResult(NamedTuple):
    status_changed_on_qualification: bool


def handle_ai_answer(
    chatbot: amo.models.AmoChatBot,
    ai_answer: amo_ai.AIAnswer,
    lead_id: int,
    contact_id: int,
    *,
    tlogger: TraceLogger,
) -> AnswerHandlingResult:

    if ai_answer.payload.lead_info:
        amo_fields.update_entity_fields(
            account=chatbot.account,
            entity=amo_api.EntityEnum.LEADS,
            instance_id=lead_id,
            fields_values=ai_answer.payload.lead_info,
            tlogger=tlogger,
        )
    else:
        tlogger.info("Lead info wasn't recognized by AI")

    if ai_answer.payload.contacts:
        amo_fields.update_entity_fields(
            account=chatbot.account,
            entity=amo_api.EntityEnum.CONTACTS,
            instance_id=contact_id,
            fields_values=ai_answer.payload.contacts,
            tlogger=tlogger,
        )
    else:
        tlogger.info("Contact info wasn't recognized by AI")

    status_changed_on_qualification = qualification.change_status_if_qualification(
        chatbot=chatbot,
        lead_id=lead_id,
        contact_id=contact_id,
        tlogger=tlogger,
    )

    if (
        ai_answer.payload.new_status
        and not status_changed_on_qualification
        and not chatbot.change_status_only_when_qualification
    ):
        lead = amo_api.get_lead(chatbot.account, lead_id, tlogger=tlogger)

        status = amo_pipelines.get_status_by_name(
            account=chatbot.account,
            pipeline_id=lead.pipeline_id,
            status_name=ai_answer.payload.new_status,
            tlogger=tlogger,
        )

        if lead.status_id != status.id:
            amo_leads.change_lead_status(
                account=chatbot.account,
                lead_id=lead.id,
                status_id=status.id,
                tlogger=tlogger,
            )

    return AnswerHandlingResult(status_changed_on_qualification)
