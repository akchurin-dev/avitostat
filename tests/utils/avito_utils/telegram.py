from aiogram.types import Message
from loguru import logger

from tests.utils import telegram


def check_new_summaries(last_message_id: int, new_summaries_count: int) -> list[Message]:
    new_summaries = get_new_summaries(last_message_id)
    logger.info(f"New summaries {len(new_summaries)}")
    assert len(new_summaries) == new_summaries_count, f"Bot sent {len(new_summaries)} summaries, but expected {new_summaries_count}"
    return new_summaries


def get_new_summaries(last_message_id: int):
    new_messages = telegram.get_new_messages_in_summary_chat(last_message_id)
    return [msg for msg in new_messages if is_summary(msg)]


def is_summary(message: Message) -> bool:
    if message.from_user is None:
        return False

    if message.from_user.id != telegram.summary_sender_bot_id():
        return False

    if message.text is None:
        return False

    return message.text.startswith("🎉 Новый клиент из AVITO 🎉")
