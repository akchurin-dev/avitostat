import datetime
from typing import Literal

from loguru import logger
from pydantic import BaseModel

from tests import config as global_config
from tests.config import avito_config
from tests.utils.avito_utils import avito_api
from tests.utils.avito_utils import avito_tokens


class ChatInfo(BaseModel):
    id: str
    users_name: list[str]
    last_message_id: str
    last_message_text: str

    @staticmethod
    def model_validate_avito_chat(chat: dict):
        msg = chat.get("last_message", {}).get("content", {}).get("text")
        if msg is None:
            msg = "<" + chat.get("last_message", {}).get("type") + ">"

        return ChatInfo(
            id=chat.get("id", None),
            users_name=[user.get("name") for user in chat.get("users", [])],
            last_message_id=chat.get("last_message", {}).get("id"),
            last_message_text=msg[:50],
        )


class AvitoMessage(BaseModel):
    id: str
    author_id: int
    created: datetime.datetime
    content: dict
    type: str
    direction: Literal["in", "out"]
    isRead: bool
    read: datetime.datetime | None = None


@avito_tokens.update_tokens_in_test_conf_decorator
def get_chats(limit: int) -> list[ChatInfo]:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/getChatByIdV2 """

    action = f"/messenger/v2/accounts/{avito_config.config.seller_avito_account_id}/chats"

    response = avito_api.get(avito_account_id=avito_config.config.seller_avito_account_id, action=action, params={"limit": limit})
    response.raise_for_status()

    chats: list[ChatInfo] = []

    for chat in response.json().get("chats", []):
        chats.append(ChatInfo.model_validate_avito_chat(chat))

    return chats


@avito_tokens.update_tokens_in_test_conf_decorator
def get_chat_info(chat_id: str) -> ChatInfo | None:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/getChatByIdV2 """

    action = f"/messenger/v2/accounts/{avito_config.config.seller_avito_account_id}/chats/{chat_id}"

    response = avito_api.get(avito_config.config.seller_avito_account_id, action)

    if response.status_code == 404:
        return None

    response.raise_for_status()

    return ChatInfo.model_validate_avito_chat(response.json())


@avito_tokens.update_tokens_in_test_conf_decorator
def get_messages(limit: int, offset: int = 0) -> list[AvitoMessage]:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/getMessagesV3 """

    action = f"/messenger/v3/accounts/{avito_config.config.seller_avito_account_id}/chats/{avito_config.config.avito_chat_id}/messages/"

    params = {
        "limit": limit,
        "offset": offset,
    }

    response = avito_api.get(avito_config.config.seller_avito_account_id, action, params=params)
    response.raise_for_status()

    if response.is_success:
        mark_chat_as_readed(avito_config.config.seller_avito_account_id)
    
    res_data = response.json()

    return [AvitoMessage.model_validate(msg) for msg in res_data["messages"]]


def get_new_messages(last_message_id: str | None) -> list[AvitoMessage]:
    messages: list[AvitoMessage] = []

    limit = 50
    offset = 0

    while True:
        new_messages = get_messages(limit, offset)
        messages.extend(new_messages)
        offset += limit

        if len(new_messages) == 0 or last_message_id in [msg.id for msg in new_messages]:
            break

    new_messages: list[AvitoMessage] = []

    for msg in messages:
        if msg.id == last_message_id:
            break

        new_messages.append(msg)

    return new_messages


def get_new_outgoing_messages_id(last_message_id: str | None) -> list[str]:
    messages: list[AvitoMessage] = get_new_messages(last_message_id)
    new_outgoing_messages: list[str] = []

    for msg in messages:
        if msg.id == last_message_id:
            break

        if msg.direction == "out":
            new_outgoing_messages.append(msg.id)

    return new_outgoing_messages


def check_new_outgoing_messages(last_message_id: str | None, new_messages_count: int) -> list[str]:
    """ Returns ids of new outgoing messages """

    new_outgoing_messages = get_new_outgoing_messages_id(last_message_id)
    logger.info(f"New outgoing messages {len(new_outgoing_messages)}")
    assert len(new_outgoing_messages) == new_messages_count, f"Bot sent {len(new_outgoing_messages)} messages, but expected {new_messages_count}"
    return new_outgoing_messages


def get_last_message_id_in_avito_chat() -> str | None:
    messages = get_messages(limit=1)

    if len(messages) == 0:
        return None

    return messages[0].id


def send_message_from_client_account(message: str):
    send_message(
        author_account_id=global_config.CUSTOMER_AVITO_ACCOUNT_ID,
        message=message,
    )


def send_message_from_seller_account(message: str):
    send_message(
        author_account_id=avito_config.config.seller_avito_account_id,
        message=message,
    )


def send_message(author_account_id: int, message: str):
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/postSendMessage """

    action = f"/messenger/v1/accounts/{author_account_id}/chats/{avito_config.config.avito_chat_id}/messages"

    data = {
        "message": {
            "text": message,
        },
        "type": "text",
    }

    mark_chat_as_readed(author_account_id)

    response = avito_api.post(
        avito_account_id=author_account_id,
        action=action,
        json=data,
    )
    response.raise_for_status()


def mark_chat_as_readed(avito_account_id: int):
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/chatRead """

    action = f"/messenger/v1/accounts/{avito_account_id}/chats/{avito_config.config.avito_chat_id}/read"

    response = avito_api.post(avito_account_id, action)
    response.raise_for_status()
