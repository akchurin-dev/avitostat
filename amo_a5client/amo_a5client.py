import datetime

from amo_a5client.utils import amo_avito_links


ORIGIN_NAME = "a5client"


def handle_message_from_amo(
    account_id: int,
    contact_id: int,
    message_created_at: datetime.datetime,
    text: str,
    author_name: str,
) -> None:

    amo_avito_links.remember_amo_message(
        amo_account_id=account_id,
        contact_id=contact_id,
        message_created_at=message_created_at,
        text=text,
        author_name=author_name,
    )


def handle_message_from_avito() -> None:
    pass
