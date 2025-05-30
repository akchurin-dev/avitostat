from typing import NamedTuple

import amo_a5client.models


class Message(NamedTuple):
    message_created_at: int
    text: str
    author_name: str


class AmoContact(NamedTuple):
    amo_account_id: int
    contact_id: int


_messages_to_amo_contacts: dict[Message, AmoContact] = {}
_old_messages: set[Message] = set()


def remember_amo_message(
    amo_account_id: int,
    contact_id: int,
    message_created_at_ts: int,
    text: str,
    author_name: str,
) -> None:

    contact_exists = amo_a5client.models.AmoContactAvitoChatLink.objects.filter(
        amo_account_id=amo_account_id,
        contact_id=contact_id,
    ).exists()

    if contact_exists:
        return

    message = Message(message_created_at_ts, text, author_name)
    amo_contact = AmoContact(amo_account_id, contact_id)

    _messages_to_amo_contacts[message] = amo_contact


def get_amo_contact_by_avito_message(
    avito_account_id: int,
    chat_id: str,
    message_created_at_ts: int,
    text: str,
    author_name: str
) -> amo_a5client.models.AmoContactAvitoChatLink | None:

    amo_contact_avito_chat_link = amo_a5client.models.AmoContactAvitoChatLink.objects.filter(
        avito_account_id=avito_account_id,
        chat_id=chat_id,
    ).first()

    if amo_contact_avito_chat_link:
        return amo_contact_avito_chat_link

    message = Message(message_created_at_ts, text, author_name)
    amo_contact = _messages_to_amo_contacts.get(message)

    if amo_contact:
        return amo_a5client.models.AmoContactAvitoChatLink.objects.create(
            amo_account_id=amo_contact.amo_account_id,
            contact_id=amo_contact.contact_id,
            avito_account_id=avito_account_id,
            chat_id=chat_id,
        )

    return None


# TODO call every 10 seconds
def clear_queue():
    global old_messages

    for old_message in _old_messages:
        del _messages_to_amo_contacts[old_message]

    old_messages = set(_messages_to_amo_contacts.keys())
