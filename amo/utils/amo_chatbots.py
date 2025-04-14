from django.db.models import QuerySet

import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def define_chatbot(account_id: int, lead_id: int, origin: str, *, tlogger: TraceLogger) -> amo.models.AmoChatBot | None:
    chatbots = amo.models.AmoChatBot.get_available_chat_bots()
    chatbot = filter_by_pipeline(chatbots, account_id, lead_id, tlogger=tlogger)

    if chatbot is None:
        tlogger.info("Chatbot not found")
        return None

    if not origin_handled_by_chatbot(chatbot, origin):
        tlogger.info(f"Chatbot '{chatbot}' doesn't handle origin '{origin}'")
        return None

    return chatbot


def filter_by_pipeline(chatbots: QuerySet, account_id: int, lead_id: int, *, tlogger: TraceLogger) -> amo.models.AmoChatBot | None:
    account = amo.models.AmoAccount.objects.get(pk=account_id)
    lead = amo_api.get_lead(account.domain, lead_id, tlogger=tlogger)
    pipeline_status = amo.models.AmoPipelineStatus.objects.get(account=account, amo_id=lead.status_id)

    if pipeline_status.chat_bot is None:
        tlogger.info(f"Pipeline status '{pipeline_status}' is not linked with chat bot")
        return None

    return chatbots.filter(pk=pipeline_status.chat_bot.pk).first()


def origin_handled_by_chatbot(chatbot: amo.models.AmoChatBot, origin: str) -> bool:
    return amo.models.AmoChatbotOriginLink.objects.filter(chatbot=chatbot, origin__code=origin).exists()
