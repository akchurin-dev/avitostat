from typing import NamedTuple

import pydantic
from pydantic import BaseModel

from ai_requests import ai_requests
from base import settings
from utils import yandex_gpt_api
from utils.logging import TraceLogger


class YandexGPTModel(NamedTuple):
    name: str
    uri: str


class YandexGPTModels:
    GPT_5_LITE = YandexGPTModel("GPT 5 Lite", "gpt://b1gl2js1crnhmb87t4vt/yandexgpt-lite/latest")


def create_completion(
    messages: list[yandex_gpt_api.YandexGPTMessage],
    schema: dict | None = None,
    reasoning_mode: yandex_gpt_api.ReasoningMode = yandex_gpt_api.ReasoningMode.DISABLED,
    temperature: float = 0.6,
    max_tokens: int = 2000,
    *,
    tag: str,
    tlogger: TraceLogger,
) -> yandex_gpt_api.CompletionResult:

    gpt_model = YandexGPTModels.GPT_5_LITE
    error = None

    for _ in range(settings.AI_RETRIES):
        try:
            completion = yandex_gpt_api.create_completion(
                model_uri=gpt_model.uri,
                messages=messages,
                schema=schema,
                reasoning_mode=reasoning_mode,
                temperature=temperature,
                max_tokens=max_tokens,
                tlogger=tlogger,
            )
            ai_requests.create_from_yandex_gpt_completion(tag, gpt_model.name, completion, tlogger=tlogger)
            return completion
        except Exception as e:
            error = e
            tlogger.info({
                "title": "Error ehen yandex gpt request",
                "error": e,
            })

    assert error
    raise error


def parse_completion(
    messages: list[yandex_gpt_api.YandexGPTMessage],
    model: type[BaseModel],
    reasoning_mode: yandex_gpt_api.ReasoningMode = yandex_gpt_api.ReasoningMode.DISABLED,
    temperature: float = 0.6,
    max_tokens: int = 2000,
    *,
    tag: str,
    tlogger: TraceLogger,
) -> tuple[yandex_gpt_api.CompletionResult, BaseModel]:

    gpt_model = YandexGPTModels.GPT_5_LITE
    error = None

    for _ in range(settings.AI_RETRIES):
        try:
            completion = yandex_gpt_api.create_completion(
                model_uri=gpt_model.uri,
                messages=messages,
                schema=model.model_json_schema(),
                reasoning_mode=reasoning_mode,
                temperature=temperature,
                max_tokens=max_tokens,
                tlogger=tlogger,
            )
            ai_requests.create_from_yandex_gpt_completion(tag, gpt_model.name, completion, tlogger=tlogger)
            return completion, model.model_validate_json(completion.alternatives[0].message.text)
        except pydantic.ValidationError as e:
            error = e
            tlogger.info({
                "title": "Invalid gpt response",
                "error": e,
            })

    assert error
    raise error


def openai_input_message_to_yandex_gpt_message(message: dict) -> yandex_gpt_api.YandexGPTMessage:
    role = message["role"]

    if isinstance(message["content"], str):
        text = message["content"]
    elif "image_url" in message["content"]:
        text = "<Изображение>"
    else:
        text = "<Сообщение неизвестного типа>"

    return {
        "role": role,
        "text": text,
    }
