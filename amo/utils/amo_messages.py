import datetime
from typing import NamedTuple

from pydantic import BaseModel

import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


class Message(BaseModel):
    id: str
    incoming: bool
    chat_id: str
    talk_id: int
    text: str | None
    created_at: datetime.datetime


class Talk(NamedTuple):
    messages: list[Message]
    opened: bool


def get_lead_chat(account_id: str, lead_id: str, talk_id: int, tlogger: TraceLogger) -> Talk:
    events = amo_api.get_lead_events(account_id, lead_id, tlogger=tlogger)

    # type 89 для входящих сообщений, 90 - для исходящих 
    message_events = [e for e in events if e["type"] in [89, 90] and e["data"]["dialog"]["id"] == talk_id]

    messages = [
        Message(
            id=e["data"]["id"],
            incoming=e["type"] == 89,
            chat_id=e["data"]["chat_id"],
            talk_id=e["data"]["dialog"]["id"],
            text=e["data"]["message"]["text"] if e["data"]["message"]["type"] == "text" else None,
            created_at=e["data"]["created_at"],
        ) for e in message_events
    ]
    messages.sort(key=lambda m: m.created_at)
    _print_chat(messages, tlogger=tlogger)

    return Talk(
        messages=messages,
        opened=message_events[0]["data"]["dialog"]["opened"],
    )


def manager_interfere(account_id: str, lead_id: str, messages: list[Message]) -> bool:
    chatbot_answers = amo.models.AmoChatBotTask.objects.filter(
        account_id=account_id,
        lead_id=lead_id,
    )
    chatbot_answers_id = [task.message_id for task in chatbot_answers]
    messages_id = {msg.id for msg in messages if not msg.incoming}

    manager_answers_id = messages_id.difference(chatbot_answers_id)
    return len(manager_answers_id) > 0


def to_legacy_format(messages: list[Message]) -> list[dict]:
    messages_legacy_format = [{
        "type": "text" if m.text else "not-text",
        "direction": "in" if m.incoming else "out",
        "content": {
            "text": m.text,
        }
    } for m in messages]

    return messages_legacy_format


def _print_chat(messages: list[Message], tlogger: TraceLogger) -> None:
    lines = ["Read chat:"]

    for msg in messages:
        line_prefix = "in" if msg.incoming else "out"
        lines.append(f"{line_prefix} ({msg.id}): {msg.text}")

    tlogger.info("\n".join(lines))
