import datetime
import logging
from typing import TypeVar

import pytz
import re

import messaging.api
from avito_account.models.excluded_items import ExcludedItem
from avito_account.models.models import AvitoAccount, WorkSchedule
from utils.logging import TraceLogger


logger = logging.getLogger(__name__)
manager_pattern = re.compile(r'^([А-ЯЁ][а-яё]+(?:\s[А-ЯЁ][а-яё]+){1,2}):\s*\n')


ChatType = TypeVar("ChatType", bound=messaging.api.Chat)


class ChatWithManagerName(messaging.api.Chat):
    manager_name: str | None


async def get_ready_chats(avito_account: AvitoAccount, period: str = "week") -> tuple[list, list]:
    chats = list(messaging.api.get_chats(avito_account, period=period))
    chats = filter_chats_for_last_period(chats, period)
    chats = messaging.api.get_chats_last_50_messages(avito_account, chats, tlogger=TraceLogger())
    chats_with_manager = adding_manager_info_for_chats(chats)
    chats_with_manager = filter_chats_only_with_text(chats_with_manager)
    chats_with_manager = await schedule_filter_chats(chats_with_manager, avito_account)
    chats_without_excluded_sellings = await excluded_items_filter_chats(chats_with_manager, avito_account)

    return chats_without_excluded_sellings, chats_with_manager


def filter_chats_for_last_period(chats: list[messaging.api.Chat], period: str = "week") -> list[messaging.api.Chat]:
    filtered_chats = []
    now = datetime.datetime.now()

    period_to_days = {
        "day": 1,
        "week": 7,
        "month": 30
    }

    max_timedelta_days = period_to_days[period]

    for chat in chats:
        chat_timestamp = chat.get('updated')
        assert chat_timestamp
        updated = datetime.datetime.fromtimestamp(chat_timestamp)
        timedelta = now - updated

        if timedelta.days <= max_timedelta_days:
            filtered_chats.append(chat)

    logger.warning(f"{len(filtered_chats)} chats loaded")

    return filtered_chats


def adding_manager_info_for_chats(chats: list[messaging.api.Chat]) -> list[ChatWithManagerName]:
    new_chats: list[ChatWithManagerName] = []

    for chat in chats:
        new_chat: ChatWithManagerName = {'manager_name': None, **chat}
        new_chats.append(new_chat)

        for message in new_chat.get('messages', []):
            if message["direction"] != 'out':
                continue

            text_content = message["content"].get("text")
            if text_content is None:
                text_content = ""

            match = manager_pattern.match(text_content)

            if match:
                manager_name = match.group(1)
                new_chat['manager_name'] = manager_name
                break

    new_chats.sort(key=lambda x: (x['manager_name'] is None, x['manager_name']))

    return new_chats


def filter_chats_only_with_text(chats: list[ChatType]) -> list[ChatType]:
    filtered_chats: list[ChatType] = []

    for chat in chats:
        messages = None
        if "messages" in chat:
            messages = chat["messages"]

        if messages is None or len(messages) == 0:
            continue

        if messages[0]["direction"] == 'out':  # Skip chats started by manager
            continue

        if any(msg["type"] == "text" for msg in messages):
            filtered_chats.append(chat)

    return filtered_chats


def filter_by_bot_answered_chat_ids(chats, current_ids):
    filtered_chats = []
    for chat in chats:
        if chat.get("id") in current_ids:
            filtered_chats.append(chat)
    return filtered_chats


async def schedule_filter_chats(chats: list[ChatWithManagerName], avito_account: AvitoAccount) -> list[ChatWithManagerName]:
    filtered_chats: list[ChatWithManagerName] = []

    schedule = await WorkSchedule.objects.filter(avito_account=avito_account).alast()
    if schedule is None:
        schedule = await WorkSchedule.objects.aget(id=1)

    for chat in chats:
        timestamp = chat.get('created')
        assert timestamp
        moscow_tz = pytz.timezone('Europe/Moscow')
        datetime_tz = datetime.datetime.fromtimestamp(timestamp, tz=moscow_tz)

        weekday = datetime_tz.weekday()
        start_time = end_time = None

        if weekday < 5:  # Понедельник-Пятница
            start_time = schedule.weekday_start
            end_time = schedule.weekday_end

        if weekday == 5 and schedule.saturday_is_day_off:  # Суббота
            start_time = schedule.saturday_start
            end_time = schedule.saturday_end

        if weekday == 6 and schedule.sunday_is_day_off:  # Воскресенье
            start_time = schedule.sunday_start
            end_time = schedule.sunday_end

        if start_time is None or end_time is None:
            continue

        start_dt = moscow_tz.localize(datetime.datetime.combine(datetime_tz.date(), start_time))
        end_dt = moscow_tz.localize(datetime.datetime.combine(datetime_tz.date(), end_time))

        if start_dt <= datetime_tz <= end_dt:
            filtered_chats.append(chat)

    return filtered_chats


async def excluded_items_filter_chats(
    fil_chats_by_sched: list[ChatWithManagerName],
    avito_account: AvitoAccount,
) -> list[ChatWithManagerName]:

    filtered_chats: list[ChatWithManagerName] = []
    excluded_ids = {ei.id async for ei in ExcludedItem.objects.filter(avito_account_id=avito_account.pk)}

    for chat in fil_chats_by_sched:
        context = chat.get("context")
        assert context

        if context["value"].get("id") not in excluded_ids:
            filtered_chats.append(chat)

    return filtered_chats
