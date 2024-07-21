from datetime import datetime
from messaging.utils_duration import get_answer_durations_seconds
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


async def get_header_with_statistics(actual_chats: list, actual_chats_with_messages: list):
    statistics = {}
    #TODO First touch
    total_first_touches = []

    for chat in actual_chats_with_messages:
        messages = chat.get("messages")
        first_incoming_time = None
        first_outgoing_time = None

        for message in messages:
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
        statistics['first_touches_average'] = average_first_touches_str

    #TODO Messages in chat count average
    counts = [len([chat for chat in chat.get("messages") if chat.get("direction") == "out"]) for chat in actual_chats]
    messages_in_chat_average = sum(counts) / len(counts)
    statistics["messages_count_in_chat_average"] = messages_in_chat_average

    # TODO Duration average
    durations = await get_answer_durations_seconds(actual_chats_with_messages)
    total_sum = sum([chat[0] for chat in durations])
    total_len = len(durations)
    if total_sum > 0 and total_len > 0:
        average_duration = total_sum / total_len
        average_duration_formatted = await convert_seconds(average_duration)
        statistics["answers_duration_average"] = average_duration_formatted

    return statistics
