from typing import NamedTuple

import amo.models
from amo.utils import amo_api
from amo.utils import amo_chatbots
from amo.utils import amo_leads
from utils.logging import TraceLogger


class DefinedChatbotLead(NamedTuple):
    chatbot: amo.models.AmoChatBot
    lead: amo_api.Lead


def define_chatbot_and_lead(
    account: amo.models.AmoAccount,
    contact_id: int,
    advised_lead_id: int | None,
    origin: str | None = None,
    note_author_name: str | None = None,
    *,
    tlogger: TraceLogger,
) -> DefinedChatbotLead | None:

    open_leads = amo_leads.get_open_leads_by_contact(
        account=account,
        contact_id=contact_id,
        advised_lead_id=advised_lead_id,
        tlogger=tlogger,
    )

    if len(open_leads) == 0:
        tlogger.info("Open lead isn't found")
        return None

    possible_chatbots = amo_chatbots.get_possible_chatbots(
        account=account,
        possible_leads=open_leads,
        origin=origin,
        note_author_name=note_author_name,
        tlogger=tlogger,
    )

    if len(possible_chatbots) == 0:
        return None

    for chatbot in possible_chatbots:
        statuses_handled_by_chatbot = set(
            amo.models.AmoPipelineStatusChatbotLink.objects
            .filter(chatbot=chatbot)
            .values_list("status__amo_id", flat=True)
        )

        for lead in open_leads:
            if lead.status_id in statuses_handled_by_chatbot:
                return DefinedChatbotLead(chatbot, lead)

    return None
