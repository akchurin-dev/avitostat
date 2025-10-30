import json
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from typing import NamedTuple

from pydantic import BaseModel
from pydantic import Field

import amo.models
from amo.utils import amo_api
from utils.logging import TraceLogger


MAX_MESSAGE_AGE = timedelta(days=31)


class ChatCreated(BaseModel):
    class SocialProfile(BaseModel):
        id: int
        profile_data_json: str = Field(alias="profile_data")
        chat_id: str = ""
        entity_id: int
        service: str
        main: int
        hidden: bool
        service_icon: str
        code: str

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.chat_id = json.loads(self.profile_data_json)["chat_id"]

    id: str
    group_id: str
    users: list
    token: str
    source_id: int
    source_name: str
    social_profile: list[SocialProfile]
    contact_amojo_id: str


class MessageTypeEnum(Enum):
    PICTURE = amo.models.AmoChatBotTask.MessageType.PICTURE.value  # type: ignore
    TEXT = amo.models.AmoChatBotTask.MessageType.TEXT.value  # type: ignore
    VOICE = amo.models.AmoChatBotTask.MessageType.VOICE.value  # type: ignore


class Message(BaseModel):
    id: str
    incoming: bool
    chat_id: str
    talk_id: int
    type: MessageTypeEnum
    text: str | None
    file_url: str | None
    created_at: datetime


class Talk(NamedTuple):
    messages: list[Message]
    opened: bool | None


SUPPORTED_MESSAGE_TYPES = {mt.value for mt in MessageTypeEnum}


def get_lead_chat(account: amo.models.AmoAccount, lead_id: int, tlogger: TraceLogger) -> Talk:
    events = amo_api.get_lead_events(account.pk, str(lead_id), tlogger=tlogger)

    # lead_talks: list[int] = list(
    #     amo.models.AmoTalkLeadLink.objects
    #     .filter(account=account, lead_id=lead_id)
    #     .values_list("talk_id", flat=True)
    # )

    # type 89 для входящих сообщений, 90 - для исходящих
    message_events = [e for e in events if e["type"] in [89, 90]]
    # message_events = [e for e in message_events if e["data"]["dialog"]["id"] in lead_talks]

    messages: list[Message] = []
    now = datetime.now(timezone.utc)

    for event in message_events:
        created_at = datetime.fromtimestamp(event["data"]["created_at"], timezone.utc)
        if (now - created_at) > MAX_MESSAGE_AGE:
            break

        message_type = event["data"]["message"]["type"]

        text = None
        if message_type == MessageTypeEnum.TEXT.value:
            text = event["data"]["message"]["text"]

        file_link = None
        if message_type in [MessageTypeEnum.PICTURE.value, MessageTypeEnum.VOICE.value]:
            file_link = event["data"]["message"]["attachment"]["media"]

        if text is None and file_link is None:
            tlogger.info(f"Skip message event. Unknown type '{message_type}'")
            continue

        messages.append(Message(
            id=event["data"]["id"],
            incoming=event["type"] == 89,
            chat_id=event["data"]["chat_id"],
            talk_id=event["data"]["dialog"]["id"],
            type=MessageTypeEnum(message_type),
            text=text,
            file_url=file_link,
            created_at=created_at,
        ))

    messages.sort(key=lambda m: m.created_at)
    _print_chat(messages, tlogger=tlogger)

    talk_opened = None
    if len(message_events) > 0:
        talk_opened = message_events[0]["data"]["dialog"]["opened"]

    return Talk(
        messages=messages,
        opened=talk_opened,
    )


def create_chat_and_talk(account: amo.models.AmoAccount, contact: amo_api.Contact, *, tlogger: TraceLogger) -> str:
    """ Create chat and talk. Return chat_id """

    chat_create_config = amo.models.AmoChatCreateConfig.objects.filter(account=account).first()

    if chat_create_config is None:
        raise Exception(f"Chat create config not found for account '{account.domain}'")

    chat = create_chat(chat_create_config, contact, tlogger=tlogger)
    chats_ids = [sp.chat_id for sp in chat.social_profile if sp.code == chat_create_config.source.origin]
    create_talk(account, chats_ids, tlogger=tlogger)

    return chat.id


def create_chat(
    config: amo.models.AmoChatCreateConfig,
    contact: amo_api.Contact,
    *,
    tlogger: TraceLogger,
) -> ChatCreated:

    action = "/ajax/v1/chats/create"

    if contact.custom_fields_values is None:
        raise Exception(f"Contact doesn't have fields")

    contact_fields_values = {fv.field_name: fv.values[0].value for fv in contact.custom_fields_values}
    phone = contact_fields_values.get(config.phone_number_field)

    if phone is None:
        raise Exception(f"Field '{config.phone_number_field}' not found in contact")

    scope_id = config.channel_id + "_" + config.account.amojo_id

    data = {
        "request": {
            "chats": {
                "create": {
                    "type": "external",
                    "entity_id": contact.id,
                    "entity_type": 1,
                    "phone": phone,
                    "source": {
                        "scope_id": scope_id,
                        "source_id": config.source.amo_id,
                        "origin": config.source.origin,
                    },
                },
            },
        },
    }

    response = amo_api._request_with_csrf(
        method="POST",
        account_id=config.account.amo_id,
        action=action,
        json=data,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return ChatCreated.model_validate(response.json()["response"]["chats"]["create"])


def create_talk(account: amo.models.AmoAccount, chats_ids: list[str], *, tlogger: TraceLogger) -> None:
    action = "/ajax/v2/talks"

    data = {"chats_ids": chats_ids}

    response = amo_api._request_with_csrf(
        method="POST",
        account_id=account.amo_id,
        action=action,
        json=data,
        tlogger=tlogger,
    )
    response.raise_for_status()


def define_message_type(text: str, attachment_type: str | None) -> MessageTypeEnum | None:
    if text:
        return MessageTypeEnum.TEXT

    if attachment_type in SUPPORTED_MESSAGE_TYPES:
        return MessageTypeEnum(attachment_type)

    return None


def manager_interfere(account_id: str, lead_id: str, messages: list[Message]) -> bool:
    chatbot_answers = amo.models.AmoChatBotTask.objects.filter(
        account_id=account_id,
        lead_id=lead_id,
    )
    first_message_at = min([chatbot_answer.message_created_at for chatbot_answer in chatbot_answers])
    outgoing_messages = [msg for msg in messages if not msg.incoming and msg.created_at >= first_message_at]

    for message in outgoing_messages:
        for chatbot_answer in chatbot_answers:
            ts_diff = timedelta()
            if chatbot_answer.answered_at is not None:
                ts_diff = chatbot_answer.answered_at - message.created_at

            if ts_diff < timedelta(seconds=5) and chatbot_answer.answer_text == message.text:
                break
        else:
            return True

    return False


def is_message_actual(task: amo.models.AmoChatBotTask, messages: list[Message], *, tlogger: TraceLogger) -> bool:
    chatbot_answers: set[str | None] = {
        t.answer_text
            for t in amo.models.AmoChatBotTask.get_tasks_by_chat(task.account, task.chat_id)
    }

    for i in range(len(messages) - 1, -1, -1):
        if messages[i].created_at <= task.message_created_at:
            break

        if messages[i].incoming:
            tlogger.info(f"Found newer incoming message ({messages[i].id}): {messages[i].text}")
            return False

        if not messages[i].incoming and messages[i].text not in chatbot_answers:
            tlogger.info(f"Found newer message outgoing not from bot ({messages[i].id}): {messages[i].text}")
            return False

    tlogger.info("Message is actual")
    return True


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
    if len(messages) == 0:
        tlogger.info("No messages")
        return

    lines = ["Read chat:"]

    for msg in messages:
        line_prefix = "in" if msg.incoming else "out"

        if msg.type == MessageTypeEnum.TEXT:
            lines.append(f"{line_prefix} ({msg.id}): {msg.text}")
            continue

        lines.append(f"{line_prefix} ({msg.id}): {msg.type.value} - {msg.file_url}")

    tlogger.info(lines)
