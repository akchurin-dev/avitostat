import datetime

import pytz

import chat_bot.models
from utils.logging import TraceLogger


moscow_tz = pytz.timezone('Europe/Moscow')


def check_chatbot_worktime_now(chatbot: chat_bot.models.AiChatBot) -> bool:
    now = datetime.datetime.now(tz=moscow_tz)
    start = moscow_tz.localize(datetime.datetime.combine(now.date(), chatbot.work_time_from))

    # Если рабочее время заканчивается на следующий день
    if chatbot.work_time_to < chatbot.work_time_from:
        stop = moscow_tz.localize(
            datetime.datetime.combine(now.date() + datetime.timedelta(days=1), chatbot.work_time_to)
        )
    else:
        stop = moscow_tz.localize(datetime.datetime.combine(now.date(), chatbot.work_time_to))

    return start <= now <= stop


def check_chatbot_shutdown_for_chat(chat_id, chatbot: chat_bot.models.AiChatBot, *, tlogger: TraceLogger) -> bool:
    chat_stopped = chat_bot.models.ChatBotTask.objects.filter(chat_id=chat_id, chat_shutdown_by_user=True,).exists()
    stopped = chat_stopped and chatbot.shutdown_after_manager

    tlogger.info(f"chat_stopped by manager manually answers - {chat_stopped}")

    return stopped
