from enum import Enum

from openai.types.responses import ResponseInputParam
from pydantic import BaseModel

from chat_bot.models import DialogTrigger
from chat_bot.utils import messages_formating
from messaging.api import ChatMessage
from utils import ai_helper
from utils.logging import TraceLogger


SYSTEM_PROMPT_BASE = """
Ты — система мониторинга сообщений чата с клиентами. 
Твоя задача — определять, срабатывает ли триггер по заданному условию.

Условие для срабатывания:
"""


class ConditionMatchLevel(Enum):
    NOT_COMPLETED = "Не выполнено"
    PARTICULARY_COMPLETED = "Выполнено частично"
    FULLY_COMPLETED = "Выполнено полностью"


class TriggerConditionCheckResult(BaseModel):
    condition_match_level: ConditionMatchLevel
    short_explanation: str


def check_trigger_condition(trigger: DialogTrigger, messages: list[ChatMessage], tlogger: TraceLogger) -> TriggerConditionCheckResult:
    _, trigger_condition_check_result = ai_helper.parse_completion(
        openai_input=_get_openai_input(trigger, messages, tlogger=tlogger),
        model=TriggerConditionCheckResult,
        tag=f"Avito | {trigger.chatbot.account.name} | check trigger condition",
        tlogger=tlogger,
    )

    return trigger_condition_check_result


def _get_openai_input(trigger: DialogTrigger, messages: list[ChatMessage], *, tlogger: TraceLogger) -> ResponseInputParam:
    messages_gpt_fmt = messages_formating.avito_chat_to_gpt_format(messages, transcriptions=None)

    ai_input: ResponseInputParam = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT_BASE + trigger.additional_condition,
        },
        {
            "role": "user",
            "content": "Чат с клиентом:\n" + messages_formating.gpt_format_to_str(messages_gpt_fmt),
        },
    ]

    # tlogger.info({"ai input": ai_input})

    return ai_input
