import io

import httpx
import openai

from base import settings
from transcriptions.models import Transcription
from utils.logging import TraceLogger


MODEL = "gpt-4o-transcribe"

client = openai.Client(api_key=settings.OPENAI_SECRET_KEY)


def create_transcription(audio_url: str, format: str, *, tlogger: TraceLogger) -> Transcription:
    audio = download_audio(audio_url)
    audio_io = io.BytesIO(audio)
    audio_io.name = "speech." + format
    text = audio_to_transcription(audio_io)

    transcription = Transcription(text=text)
    transcription.save()

    tlogger.info(f"Got transcription '{text}' for audio (url={audio_url})")

    return transcription


def audio_to_transcription(audio: io.BytesIO) -> str:
    return client.audio.transcriptions.create(model=MODEL, file=audio).text


def download_audio(url) -> bytes:
    return httpx.get(url, follow_redirects=True, timeout=30).content
