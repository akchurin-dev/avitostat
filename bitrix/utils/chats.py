import datetime

import pydantic

from bitrix.utils import bitrix_api


class Message(pydantic.BaseModel):
    id: int
    chat_id: int
    author_id: int
    date: datetime.datetime
    text: str


async def get_messages(bitrix_domain: str, dialog_id: int | str, messages_count: int) -> list[Message]:
    """ https://apidocs.bitrix24.ru/api-reference/chats/messages/im-dialog-messages-get.html """

    response = await bitrix_api.get(
        bitrix_domain=bitrix_domain,
        operation="im.dialog.messages.get",
        params={
            "DIALOG_ID": dialog_id,
            "LIMIT": messages_count,
        },
    )
    response.raise_for_status()

    data = response.json()

    return [Message.model_validate(m) for m in data["result"]["messages"]]


async def send_message(bitrix_domain: str, dialog_id: int | str, message: str):
    """ https://apidocs.bitrix24.ru/api-reference/chat-bots/messages/imbot-message-add.html """

    response = await bitrix_api.post(
        bitrix_domain=bitrix_domain,
        operation="imbot.message.add",
        json={
            "DIALOG_ID": dialog_id,
            "MESSAGE": message,
        },
    )
    response.raise_for_status()
