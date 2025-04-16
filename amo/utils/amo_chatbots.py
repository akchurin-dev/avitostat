from django.db.models import QuerySet

import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def define_chatbot(account_id: int, lead_id: int, origin: str, *, tlogger: TraceLogger) -> amo.models.AmoChatBot | None:
    chatbots = amo.models.AmoChatBot.get_available_chatbots()
    chatbot = get_by_pipeline_status(chatbots, account_id, lead_id, tlogger=tlogger)

    if chatbot is None:
        tlogger.info("Chatbot not found")
        return None

    if not origin_handled_by_chatbot(chatbot, origin):
        tlogger.info(f"Chatbot '{chatbot}' doesn't handle origin '{origin}'")
        return None

    return chatbot


def get_by_pipeline_status(chatbots: QuerySet, account_id: int, lead_id: int, *, tlogger: TraceLogger) -> amo.models.AmoChatBot | None:
    account = amo.models.AmoAccount.objects.get(pk=account_id)
    lead = amo_api.get_lead(account.domain, lead_id, tlogger=tlogger)
    status_bot_link = amo.models.AmoPipelineStatusChatbotLink.objects.filter(
        status__account=account,
        status__amo_id=lead.status_id,
    ).first()

    chatbot = None
    if status_bot_link:
        chatbot = status_bot_link.chatbot

    if chatbot is None:
        status = amo.models.AmoPipelineStatus.objects.get(
            account=account,
            pipeline_id=lead.pipeline_id,
            amo_id=lead.status_id,
        )
        tlogger.info(f"Pipeline status '{status.name}' is not linked with chat bot")
        return None

    return chatbots.filter(pk=chatbot.pk).first()


def origin_handled_by_chatbot(chatbot: amo.models.AmoChatBot, origin: str) -> bool:
    return amo.models.AmoChatbotOriginLink.objects.filter(chatbot=chatbot, origin__code=origin).exists()
