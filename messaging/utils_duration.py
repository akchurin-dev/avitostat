from datetime import datetime
from typing import Dict, Any, List

from avito_account.models.models import AvitoAccount
from messaging.api import get_calls_statistic_last_week


async def get_durations_seconds(chats: List[Dict[str, Any]]):
    duration_times = []

    for chat in chats:
        messages = chat.get("messages")
        last_in_message = None

        for message in messages:
            if message['direction'] == 'in':
                last_in_message = message
            elif message['direction'] == 'out' and last_in_message:
                in_time = datetime.fromtimestamp(last_in_message['created'])
                out_time = datetime.fromtimestamp(message['created'])
                duration = (out_time - in_time).total_seconds()

                chat_id = chat.get('id')
                manager_name = chat.get("manager_name")
                duration_times.append([duration, chat_id, manager_name])

                last_in_message = None

    return duration_times


async def get_calls_count_unique_numbers_last_week(avito_account: AvitoAccount) -> int:
    calls_statictic = await get_calls_statistic_last_week(avito_account=avito_account)
    if calls_statictic:
        total_new_calls = sum(day['new'] for day in calls_statictic['result']['items'][0]['days'])
    else:
        total_new_calls = 0
    return total_new_calls
