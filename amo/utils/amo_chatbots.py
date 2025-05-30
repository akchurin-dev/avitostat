from django.db.models import QuerySet

import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


def get_possible_chatbots(
    account: amo.models.AmoAccount,
    possible_leads: list[amo_api.Lead],
    origin: str | None = None,
    note_author_name: str | None = None,
    *,
    tlogger: TraceLogger,
) -> list[amo.models.AmoChatBot]:

    chatbots = amo.models.AmoChatBot.get_available_chatbots()
    chatbots = chatbots.filter(account=account)
    chatbots = filter_by_pipelines_statuses(chatbots, account, possible_leads, tlogger=tlogger)

    if origin is not None:
        chatbots = filter_by_origin(chatbots, origin, tlogger=tlogger)

    if note_author_name is not None:
        chatbots = filter_by_note_author(chatbots, note_author_name, tlogger=tlogger)

    chatbots_list = list(chatbots)

    if len(chatbots_list) == 0:
        tlogger.info("Chatbot not found")

    return chatbots_list


def filter_by_pipelines_statuses(
    chatbots: QuerySet,
    account: amo.models.AmoAccount,
    leads: list[amo_api.Lead],
    *,
    tlogger: TraceLogger,
) -> QuerySet[amo.models.AmoChatBot]:

    statuses_ids = [lead.status_id for lead in leads]

    status_bot_links = amo.models.AmoPipelineStatusChatbotLink.objects.filter(
        status__account=account,
        status__amo_id__in=statuses_ids,
    )

    chatbots_ids = [status_bot_link.chatbot.pk for status_bot_link in status_bot_links]

    if len(chatbots_ids) == 0:
        statuses_names = amo.models.AmoPipelineStatus.objects.filter(
            account=account,
            amo_id__in=statuses_ids,
        ).values_list("name", flat=True)
        tlogger.info(f"Active Chatbot not found for pipelines statuses {statuses_names}")

    return chatbots.filter(pk__in=chatbots_ids)


def filter_by_origin(
    chatbots: QuerySet[amo.models.AmoChatBot],
    origin: str,
    *,
    tlogger: TraceLogger,
) -> QuerySet[amo.models.AmoChatBot]:

    origin_bot_links = amo.models.AmoChatbotOriginLink.objects.filter(
        chatbot__in=chatbots,
        origin__origin=origin,
    )

    chatbots_ids = [origin_bot_link.chatbot.pk for origin_bot_link in origin_bot_links]

    if len(chatbots_ids) == 0:
        tlogger.info(f"Chatbots for origin '{origin}' aren't found")

    return chatbots.filter(pk__in=chatbots_ids)


def filter_by_note_author(
    chatbots: QuerySet[amo.models.AmoChatBot],
    note_author_name: str,
    *,
    tlogger: TraceLogger,
) -> QuerySet[amo.models.AmoChatBot]:

    chatbots_ids = (
        amo.models.HandlebleNote.objects.filter(
            chatbot__in=chatbots,
            author_name=note_author_name,
        ).values_list("chatbot_id", flat=True)
    )

    if len(chatbots_ids) == 0:
        tlogger.info(f"Chatbots for note with author '{note_author_name}' aren't found")

    return chatbots.filter(pk__in=chatbots_ids)
