from typing import NamedTuple

import amo.models
from amo.utils import amo_messages
from transcriptions import transcriptions
from utils.logging import TraceLogger


class MessageId(NamedTuple):
    chat_id: str
    message_id: str


class TranscriptionsForMessages:
    def __init__(self, messages_to_transcriptions: dict[MessageId, str]):
        self.messages_to_transcriptions = messages_to_transcriptions

    def get_transcription(self, message: amo_messages.Message) -> str:
        message_id = MessageId(message.chat_id, message.id)
        return self.messages_to_transcriptions[message_id]


def get_transcriptions_for_voice_messages(
    account: amo.models.AmoAccount,
    messages: list[amo_messages.Message],
    *,
    tlogger: TraceLogger,
) -> TranscriptionsForMessages:

    voice_messages = [m for m in messages if m.type == amo_messages.MessageTypeEnum.VOICE]

    chats_id = [m.chat_id for m in voice_messages]
    messages_ids = [m.id for m in voice_messages]

    amo_transcriptions = amo.models.AmoTranscription.objects.filter(
        chat_id__in=chats_id,
        message_id__in=messages_ids,
    ).select_related("transcription")

    messages_to_transcriptions = {MessageId(t.chat_id, t.message_id): t.transcription.text for t in amo_transcriptions}
    tlogger.info(f"Found transcriptions for messages: {messages_to_transcriptions.keys()}")

    create_transcriptions: list[amo.models.AmoTranscription] = []

    for message in voice_messages:
        message_id = MessageId(message.chat_id, message.id)

        if message_id in messages_to_transcriptions:
            continue

        assert message.file_url
        transcription = transcriptions.create_transcription(message.file_url, "m4a", tlogger=tlogger)
        messages_to_transcriptions[message_id] = transcription.text
        create_transcriptions.append(amo.models.AmoTranscription(
            account=account,
            chat_id=message.chat_id,
            message_id=message.id,
            transcription=transcription,
        ))

        tlogger.info(f"Created transcription for {message_id}")

    amo.models.AmoTranscription.objects.bulk_create(create_transcriptions)

    return TranscriptionsForMessages(messages_to_transcriptions)
