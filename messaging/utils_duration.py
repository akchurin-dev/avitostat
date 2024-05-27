import datetime
from typing import Dict, Any, List


async def get_answer_durations(chats: List[Dict[str, Any]]) -> Dict[Any, Any]:
    duration_times = []

    for chat in chats:
        messages = chat.get("messages")
        last_in_message = None

        for message in messages:
            if message['direction'] == 'in':
                last_in_message = message
            elif message['direction'] == 'out' and last_in_message:
                in_time = datetime.datetime.fromtimestamp(last_in_message['created'])
                out_time = datetime.datetime.fromtimestamp(message['created'])
                duration = (out_time - in_time).total_seconds()

                chat_id = chat.get('id')
                duration_times.append([duration, chat_id])

                last_in_message = None

    return duration_times


async def get_chats_for_week(chats: list) -> list:
    filtered_chats = []
    now = datetime.datetime.now()

    if len(chats) > 0:
        for chat in chats:
            updated = datetime.datetime.fromtimestamp(chat.get("updated"))
            timedelta = now - updated
            print(timedelta)
            if 7 >= timedelta.days > -1:
                filtered_chats.append(chat)
        return filtered_chats


async def convert_seconds(seconds):
    td = datetime.timedelta(seconds=seconds)
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} д")
    if hours > 0:
        parts.append(f"{hours} ч")
    if minutes > 0:
        parts.append(f"{minutes} м")
    if seconds > 0:
        parts.append(f"{seconds} с")

    return ": ".join(parts)


async def get_duration_statistics(chats: list):
    statistics = {}
    total_sum = sum([chat[0] for chat in chats])
    total_len = len(chats)
    if total_sum > 0 and total_len > 0:
        average_duration = total_sum / total_len
        average_duration_formatted = await convert_seconds(average_duration)
        statistics["average_duration"] = average_duration_formatted

    top_durations = sorted(chats, key=lambda x: x[0])[::-1][:10]
    top_durations_formatted = [[await convert_seconds(duration[0]), duration[1]] for duration in top_durations]
    statistics["top_durations"] = top_durations_formatted
    return statistics
