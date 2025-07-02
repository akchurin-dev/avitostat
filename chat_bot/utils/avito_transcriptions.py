import chat_bot.models
import messaging.api
from avito_account.models.models import AvitoAccount
from transcriptions import transcriptions
from utils.logging import TraceLogger


class TranscriptionsForMessages:
    def __init__(self, messages_ids_to_transcriptions: dict[str, str]):
        self.messages_ids_to_transcriptions = messages_ids_to_transcriptions

    def get_transcription(self, message: messaging.api.ChatMessage) -> str:
        return self.messages_ids_to_transcriptions[message["id"]]


def get_voice_messages_transcriptions(
    avito_account: AvitoAccount,
    chat: messaging.api.Chat,
    *,
    tlogger: TraceLogger,
) -> TranscriptionsForMessages:

    all_messages = chat.get("messages", [])
    voice_messages = [message for message in all_messages if message["type"] == "voice"]
    voice_messages_ids = [msg["id"] for msg in voice_messages]

    avito_transcriptions = chat_bot.models.AvitoTranscription.objects.filter(
        account=avito_account,
        chat_id=chat.get("id", ""),
        message_id__in=voice_messages_ids,
    ).select_related("transcription")

    messages_ids_to_transcriptions: dict[str, str] = {
        transcription.message_id: transcription.transcription.text for transcription in avito_transcriptions
    }
    tlogger.info(f"Found transcriptions for messages: {messages_ids_to_transcriptions.keys()}")

    voices_to_messages: dict[str, str] = {}

    for message in voice_messages:
        if message["id"] in messages_ids_to_transcriptions:
            continue

        voice = message["content"].get("voice")
        assert voice
        voices_to_messages[voice["voice_id"]] = message["id"]

    voices_ids_to_urls: dict[str, str] = {}
    if voice_messages:
        voices_ids_to_urls = messaging.api.get_voice_id_url_pairs(
            account=avito_account,
            voices_ids=list(voices_to_messages.keys()),
            tlogger=tlogger,
        )

    for voices_id, voice_url in voices_ids_to_urls.items():
        message_id = voices_to_messages[voices_id]
        transcription = transcriptions.create_transcription(voice_url, "ogg", tlogger=tlogger)
        messages_ids_to_transcriptions[message_id] = transcription.text
        chat_bot.models.AvitoTranscription.objects.create(
            account=avito_account,
            chat_id=chat.get("id", ""),
            message_id=message_id,
            transcription=transcription,
        )

    return TranscriptionsForMessages(messages_ids_to_transcriptions)
