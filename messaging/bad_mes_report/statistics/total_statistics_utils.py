from datetime import datetime
from messaging.utils_duration import get_second_touches_durations_seconds
from messaging.views import convert_seconds
from datetime import timedelta


def time_str_to_seconds(time_str):
    if 'days' in time_str:
        days, time_part = time_str.split(' days, ')
        days = int(days)
    elif 'day' in time_str:
        days, time_part = time_str.split(' day, ')
        days = int(days)
    else:
        days = 0
        time_part = time_str

    time_parts = list(map(int, time_part.split(':')))
    seconds = days * 86400 + time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]
    return seconds


def seconds_to_time_str(seconds):
    td = timedelta(seconds=seconds)
    return str(td)


'#73C356'  # green
'#E4A03B'  # yellow
'#C04D3D'  # red


def get_color_first_touches_average(rounded_average: int,
                                    color: str = '#C04D3D') -> str:  # default color - red
    if rounded_average >= 300:
        color = '#C04D3D'  # red
    elif 120 <= rounded_average < 300:
        color = '#E4A03B'  # yellow
    elif 1 <= rounded_average < 120:
        color = '#73C356'  # green
    return color


def get_color_second_touches_average(rounded_average: int,
                                     color: str = '#C04D3D') -> str:  # default color - red
    if rounded_average >= 420:
        color = '#C04D3D'  # red
    elif 240 <= rounded_average < 420:
        color = '#E4A03B'  # yellow
    elif 1 <= rounded_average < 240:
        color = '#73C356'  # green
    return color


def get_color_touches_count_in_chat_average(messages_count_in_chat_average: float,
                                            color: str = '#C04D3D') -> str:  # default color - red
    if messages_count_in_chat_average >= 5:
        color = '#73C356'  # green
    elif 4 <= messages_count_in_chat_average < 5:
        color = '#E4A03B'  # yellow
    elif messages_count_in_chat_average <= 3:
        color = '#C04D3D'  # red
    return color


async def get_statistics_total(filtered_chats_only_with_text: list):
    statistics = {}
    #TODO First touch
    total_first_touches = []

    for chat in filtered_chats_only_with_text:
        statistics['first_touches_average'] = {  #  Default values if cant calculate it
            "value": "не удалось рассчитать",
            "color": '#C04D3D'
        }

        first_incoming_time = None
        first_outgoing_time = None

        for message in chat.get("messages", None):
            if message['direction'] == 'in' and first_incoming_time is None:
                first_incoming_time = message['created']
            elif message['direction'] == 'out' and first_incoming_time is not None:
                first_outgoing_time = message['created']
                break

        if first_incoming_time is None:
            # If there's no incoming message, skip this chat
            continue

        import time
        if first_outgoing_time is None:
            # If there's no outgoing message, use the current timestamp
            first_outgoing_time = current_unix_time = int(time.time())

        # Calculate the elapsed time in seconds
        elapsed_time = first_outgoing_time - first_incoming_time

        # Convert the elapsed time to a human-readable format (days, hours, minutes, seconds)
        elapsed_time_str = str(datetime.utcfromtimestamp(elapsed_time) - datetime.utcfromtimestamp(0))
        total_first_touches.append(elapsed_time_str)

        # Преобразуем каждое значение времени в секунды
        seconds_list = [time_str_to_seconds(time) for time in total_first_touches]

        # Вычисляем среднее значение в секундах
        average_seconds = sum(seconds_list) / len(seconds_list)
        rounded_average = round(average_seconds)

        # Преобразуем среднее значение обратно в строку формата 'часы:минуты:секунды'
        average_first_touches_str = seconds_to_time_str(rounded_average)
        color = get_color_first_touches_average(rounded_average)
        statistics['first_touches_average'] = {
            "value": average_first_touches_str,
            "color": color
        }

    # TODO Duration average
    durations = await get_second_touches_durations_seconds(filtered_chats_only_with_text)
    total_sum = sum([chat[0] for chat in durations])
    total_len = len(durations)
    if total_sum > 0 and total_len > 0:
        average_duration = total_sum / total_len
        average_duration_formatted = await convert_seconds(average_duration)
        color = get_color_second_touches_average(average_duration)
        statistics["second_touches_duration_average"] = {
            "value": average_duration_formatted,
            "color": color
        }
    elif total_sum == 0:  # Если небыло второго касания вообще -
        statistics["second_touches_duration_average"] = {
            "value": "отсутствует",
            "color": '#C04D3D'  # red
        }

    #TODO Touches in chat count average
    counts = [len([chat for chat in chat.get("messages") if chat.get("direction") == "out"]) for chat in
              filtered_chats_only_with_text]
    touches_in_chat_average = sum(counts) / len(counts)
    color = get_color_touches_count_in_chat_average(round(touches_in_chat_average, 1))
    statistics["touches_in_chat_average"] = {
        "color": color,
        "value": round(touches_in_chat_average, 1)
    }

    return statistics


async def grouping_chats_by_managers(sorted_chats: list) -> list:
    grouped_chats = []
    if len(sorted_chats) > 0:
        grouped_chats.append({
            "manager_name": sorted_chats[0].get("manager_name"),
            "chats": [sorted_chats[0], ]
        })
        for chat in sorted_chats[1:]:
            manager_name = chat.get("manager_name")
            if grouped_chats[-1]["manager_name"] == manager_name:
                grouped_chats[-1]["chats"].append(chat)
            else:
                grouped_chats.append({
                    "manager_name": manager_name,
                    "chats": [chat, ]
                })
    return grouped_chats


async def get_stat_total_split_by_man(actual_chats_with_messages: list):
    grouped_chats = await grouping_chats_by_managers(actual_chats_with_messages)

    if len(grouped_chats) > 0:
        for manager_chats in grouped_chats:
            manager_chats["statistics"] = []
            statistics_for_manager = await get_statistics_total(
                filtered_chats_only_with_text=manager_chats.get("chats"))
            if statistics_for_manager:
                manager_chats.get("statistics").append(statistics_for_manager)

    return grouped_chats
