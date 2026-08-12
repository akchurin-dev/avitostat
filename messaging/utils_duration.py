from datetime import datetime
from typing import Dict, Any, List

from avito_account.models.models import AvitoAccount
from messaging.api import get_calls_statistic_last_week
from utils.logging import TraceLogger


async def get_durations_seconds(chats: List[Dict[str, Any]]):
    duration_times = []

    for chat in chats:
        messages = chat.get("messages", [])
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
                if duration > 0:
                    duration_times.append([duration, chat_id, manager_name])

                last_in_message = None

    return duration_times


def get_calls_count_unique_numbers_last_week(avito_account: AvitoAccount, *, tlogger: TraceLogger) -> int:
    calls_statictic = get_calls_statistic_last_week(avito_account, tlogger=tlogger)
    return sum(day.new for item in calls_statictic for day in item.days)
