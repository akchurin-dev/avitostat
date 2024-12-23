import time
from typing import Tuple, List, Any

import pytz
from asgiref.sync import sync_to_async
import re

from avito_account.models.excluded_items import ExcludedItem
from avito_account.models.models import AvitoAccount, WorkSchedule
from messaging.api import get_chats, get_chats_messages
import datetime


async def filter_chats_for_last_period(chats: list, period: str = "week") -> list:
    filtered_chats = []
    now = datetime.datetime.now()

    if len(chats) > 0:
        for chat in chats:
            updated = datetime.datetime.fromtimestamp(chat.get('updated'))
            timedelta = now - updated

            if period == "week":
                if 7 >= timedelta.days >= 0:
                    filtered_chats.append(chat)
            if period == "month":
                if 30 >= timedelta.days >= 0:
                    filtered_chats.append(chat)
        print(f"{len(filtered_chats)} chats loaded")
        return filtered_chats


def adding_manager_info_for_chats(chats):
    manager_pattern = re.compile(r'^([А-ЯЁ][а-яё]+(?:\s[А-ЯЁ][а-яё]+){1,2}):\s*\n')

    for chat in chats:
        chat['manager_name'] = None
        for message in chat.get('messages'):
            if message.get("direction") == 'out':
                text_content = message.get("content", {}).get("text", "")
                match = manager_pattern.match(text_content)
                if match:
                    manager_name = match.group(1)
                    chat['manager_name'] = manager_name
                    break
    sorted_chats = sorted(chats, key=lambda x: (x['manager_name'] is None, x['manager_name']))
    return sorted_chats


def filter_chats_only_with_text(chats):
    filtered_chats = []
    for chat in chats:
        if chat.get("messages")[0].get("direction") == 'out':  # Skip all chats initialized from Manager
            continue
        if any(message.get("type") == "text" for message in chat.get("messages", [])):
            filtered_chats.append(chat)
    return filtered_chats


async def schedule_filter_chats(filtered_chats_only_with_text: list, avito_account: AvitoAccount):
    filtered_chats = []
    schedule = await sync_to_async(WorkSchedule.objects.filter(avito_account_id=avito_account.id).last)()
    if schedule is None:
        schedule = await sync_to_async(WorkSchedule.objects.filter(id=1).last)()

    for chat in filtered_chats_only_with_text:
        timestamp = chat.get('created')
        # Московский часовой пояс
        moscow_tz = pytz.timezone('Europe/Moscow')

        # Преобразование timestamp в datetime с учётом московского часового пояса
        dt_object = datetime.datetime.fromtimestamp(timestamp, tz=moscow_tz)

        # Предположим, у нас есть объект расписания, который мы получили из базы данных
        work_schedule = schedule

        # Определяем день недели (0 - Понедельник, 6 - Воскресенье)
        weekday = dt_object.weekday()

        # Проверяем рабочие часы в зависимости от дня недели
        if weekday < 5:  # Понедельник-Пятница
            start_time = work_schedule.weekday_start
            end_time = work_schedule.weekday_end
        elif weekday == 5:  # Суббота
            if work_schedule.saturday_is_day_off:
                # print("Суббота - выходной.")
                continue
            else:
                start_time = work_schedule.saturday_start
                end_time = work_schedule.saturday_end
        elif weekday == 6:  # Воскресенье
            if work_schedule.sunday_is_day_off:
                # print("Воскресенье - выходной.")
                continue
            else:
                start_time = work_schedule.sunday_start
                end_time = work_schedule.sunday_end

        # Если день рабочий, сравниваем время
        if 'start_time' in locals() and 'end_time' in locals():
            # Преобразуем время начала и окончания работы в объекты datetime с учётом часового пояса
            start_dt = moscow_tz.localize(datetime.datetime.combine(dt_object.date(), start_time))
            end_dt = moscow_tz.localize(datetime.datetime.combine(dt_object.date(), end_time))

            if start_dt <= dt_object <= end_dt:
                # print(f"Время в рамках рабочего времени.{dt_object.time(), dt_object.weekday()}")
                filtered_chats.append(chat)
            # else:
            #     print(f"Время вне рабочего времени.{dt_object.time(), dt_object.weekday()}")

    return filtered_chats


async def get_ready_chats(avito_account: AvitoAccount, period: str = "week") -> tuple[list[Any], int] | list[Any]:
    chats = await get_chats(avito_account, period=period)
    if chats:
        # Chats with messages getting
        actual_chats = await filter_chats_for_last_period(chats)
        actual_chats_with_mes = await get_chats_messages(avito_account, actual_chats, period=period)

        #  Filtering and processing before using
        comp_mes_with_man = adding_manager_info_for_chats(actual_chats_with_mes)
        fil_chats_only_with_text = filter_chats_only_with_text(comp_mes_with_man)
        chats_without_filtering_count = len(fil_chats_only_with_text)
        fil_chats_by_sched = await schedule_filter_chats(fil_chats_only_with_text, avito_account)
        fil_by_excluded_items = await excluded_items_filter_chats(fil_chats_by_sched, avito_account)
        print(f"{len(fil_by_excluded_items)} chats after filtering")
        return fil_by_excluded_items, chats_without_filtering_count
    else:
        return []


async def excluded_items_filter_chats(fil_chats_by_sched, avito_account):
    filtered_chats = []
    excluded_items = await sync_to_async(list)(ExcludedItem.objects.filter(avito_account_id=avito_account.id))
    excluded_ids = [item.id for item in excluded_items]
    for chat in fil_chats_by_sched:
        if chat.get("context").get("value").get("id") not in excluded_ids:
            filtered_chats.append(chat)
    return filtered_chats
