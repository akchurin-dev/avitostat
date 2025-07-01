from typing import NamedTuple

from django.db.models import F, Value
from django.db.models.functions import Abs

import amo_a5client.models
from utils.logging import TraceLogger


class Message(NamedTuple):
    message_created_at: int
    text: str
    author_name: str


class AmoContact(NamedTuple):
    amo_account_id: int
    contact_id: int


MAX_MESSAGES_COUNT = 300

_messages_to_amo_contacts: dict[Message, AmoContact] = {}
_messages_queue: list[Message] = []


def remember_amo_message(
    amo_account_id: int,
    contact_id: int,
    message_created_at_ts: int,
    text: str,
    author_name: str,
    *,
    tlogger: TraceLogger,
) -> None:

    # contact_exists = amo_a5client.models.AmoContactAvitoChatLink.objects.filter(
    #     amo_account_id=amo_account_id,
    #     contact_id=contact_id,
    # ).exists()

    # if contact_exists:
    #     tlogger.info("Contact exists already")
    #     return

    message = Message(message_created_at_ts, text, author_name)
    amo_contact = AmoContact(amo_account_id, contact_id)

    _add_link_to_container(message, amo_contact, tlogger=tlogger)

    tlogger.info({"Message-AmoContact link saved": {
        "message": message,
        "amo_contact": amo_contact,
    }})


# TODO dpnt use db-models
def get_amo_contact_by_avito_message(
    avito_account_id: int,
    chat_id: str,
    message_created_at_ts: int,
    text: str,
    author_name: str,
    *,
    tlogger: TraceLogger,
) -> amo_a5client.models.AmoContactAvitoChatLink | None:

    # amo_contact_avito_chat_link = amo_a5client.models.AmoContactAvitoChatLink.objects.filter(
    #     avito_account_id=avito_account_id,
    #     chat_id=chat_id,
    # ).first()

    # if amo_contact_avito_chat_link:
    #     tlogger.info({
    #         "Found amo-contact to avito-chat link": {
    #             "chat_id": chat_id,
    #             "amo_contact": amo_contact_avito_chat_link.amo_account,
    #         }
    #     })

    #     return amo_contact_avito_chat_link

    message = Message(message_created_at_ts, text, author_name)
    # amo_contact = _messages_to_amo_contacts.get(message)

    amo_contact_model = (
        amo_a5client.models.MessageContactLink.objects.annotate(
            mca_diff=Abs(F("message_created_at") - Value(message.message_created_at)),
        )
        .filter(
            mca_diff__lte=3,
            text=message.text,
            author_name=message.author_name,
        )
        .first()
    )
    amo_contact = None
    if amo_contact_model:
        amo_contact = AmoContact(
            amo_account_id=amo_contact_model.amo_account_id,
            contact_id=amo_contact_model.contact_id,
        )

    if amo_contact is None:
        tlogger.info(f"Amo contact for message {message} not found")
        return None

    tlogger.info({
        "Create amo-contact to avito-chat link": {
            "chat_id": chat_id,
            "amo_contact": amo_contact,
        }
    })

    contact_chat_link = amo_a5client.models.AmoContactAvitoChatLink.objects.filter(
        amo_account_id=amo_contact.amo_account_id,
        contact_id=amo_contact.contact_id,
    ).first()

    if contact_chat_link:
        contact_chat_link.delete()

    return amo_a5client.models.AmoContactAvitoChatLink.objects.create(
        amo_account_id=amo_contact.amo_account_id,
        contact_id=amo_contact.contact_id,
        avito_account_id=avito_account_id,
        chat_id=chat_id,
    )


# TODO dont use db-models
def _add_link_to_container(message: Message, contact: AmoContact, *, tlogger: TraceLogger) -> None:
    # global _messages_queue

    # _messages_to_amo_contacts[message] = contact
    # _messages_queue.append(message)

    # tlogger.info(f"Messages count = {len(_messages_to_amo_contacts)}/{MAX_MESSAGES_COUNT}")

    # if len(_messages_to_amo_contacts) <= MAX_MESSAGES_COUNT:
    #     return

    # delete_count = len(_messages_to_amo_contacts) - MAX_MESSAGES_COUNT // 2

    # for i in range(delete_count):
    #     message = _messages_queue[i]
    #     del _messages_to_amo_contacts[message]

    # _messages_queue = _messages_queue[delete_count:]

    # tlogger.info(f"Container cleaned. Messages count = {len(_messages_to_amo_contacts)}")

    amo_a5client.models.MessageContactLink.objects.create(
        message_created_at = message.message_created_at,
        text = message.text,
        author_name = message.author_name,
        amo_account_id = contact.amo_account_id,
        contact_id = contact.contact_id,
    )
