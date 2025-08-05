from typing import Literal

from openai.types.responses import ResponseInputItemParam
from openai.types.responses import ResponseInputMessageContentListParam

import messaging.api
from chat_bot.utils import avito_transcriptions


def avito_chat_to_gpt_format(
    messages: list[messaging.api.ChatMessage],
    transcriptions: avito_transcriptions.TranscriptionsForMessages | None = None,
) -> list[ResponseInputItemParam]:

    formatted_messages: list[ResponseInputItemParam] = []

    for msg in messages:
        gpt_formatted = avito_message_to_gpt_format(msg, transcriptions)
        if gpt_formatted:
            formatted_messages.append(gpt_formatted)

    return formatted_messages


def avito_message_to_gpt_format(
    message: messaging.api.ChatMessage,
    transcriptions: avito_transcriptions.TranscriptionsForMessages | None = None,
) -> ResponseInputItemParam:

    role: Literal["user", "assistant"] = "user" if message["direction"] == "in" else "assistant"
    content: str | ResponseInputMessageContentListParam | None = None

    if message["type"] == "text":
        content = message["content"].get("text")

    if message["type"] == "image":
        image = message["content"].get("image")
        assert image
        content = [{
            "type": "input_image",
            "image_url": _select_image(image["sizes"]),
            "detail": "low",
        }]

    if message["type"] == "voice" and transcriptions:
        content = transcriptions.get_transcription(message)

    if content is None:
        content = "<message unavailable>"

    return {
        "role": role,
        "content": content,
    }


def gpt_format_to_str(messages: list[ResponseInputItemParam]) -> str:
    replicas: list[str] = []

    for message in messages:
        if "role" not in message or "content" not in message:
            continue

        role = "Manager"
        if message["role"] == "user":
            role = "Client"

        content = message["content"]

        if isinstance(content, str):
            text = content
        else:
            text = "Not text format"

        replicas.append(role + ": " + text)

    return "\n".join(replicas)


def _select_image(sizes_to_urls: dict[str, str]) -> str:
    MIN_SIZE = 256 * 256

    widths_heights: list[tuple[int, ...]] = [tuple(map(int, size.split("x"))) for size in sizes_to_urls.keys()]
    pixels = sorted([size[0] * size[1] for size in widths_heights])

    selected_size = pixels[-1]
    pixels = [p for p in pixels if p >= MIN_SIZE]
    if pixels:
        selected_size = pixels[0]

    width, height = [(w, h) for w, h in widths_heights if w * h == selected_size][0]

    return sizes_to_urls[f"{width}x{height}"]
