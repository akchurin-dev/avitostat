from __future__ import annotations

from typing import NamedTuple

from openai import NOT_GIVEN
from openai.types.responses import Response as OpenAIResponse
from openai.types.responses import ResponseInputItemParam
from openai.types.responses import ResponseTextConfigParam
from pydantic import BaseModel

from utils import openai_helper
from utils import yandex_gpt_helper
from utils.logging import TraceLogger
from utils.yandex_gpt_api import CompletionResult as YandexGPTCompletion


class UniversalCompletion(NamedTuple):
    answer_text: str

    input_tokens: int
    output_tokens: int
    input_details: str
    output_details: str

    @staticmethod
    def from_openai_response(response: OpenAIResponse) -> UniversalCompletion:
        return UniversalCompletion(
            answer_text=response.output_text,
            input_tokens=response.usage.input_tokens if response.usage else 0,
            output_tokens=response.usage.output_tokens if response.usage else 0,
            input_details=str(response.usage.input_tokens_details) if response.usage else "",
            output_details=str(response.usage.output_tokens_details) if response.usage else "",
        )

    @staticmethod
    def from_yandex_gpt_reponse(response: YandexGPTCompletion) -> UniversalCompletion:
        return UniversalCompletion(
            answer_text=response.alternatives[0].message.text,
            input_tokens=response.usage.input_text_tokens,
            output_tokens=response.usage.completion_tokens,
            input_details="",
            output_details=str(response.usage.completion_tokens_details),
        )


def parse_completion(
    openai_input: list[ResponseInputItemParam],
    model: type[BaseModel],
    max_output_tokens: int = 2000,
    *,
    tag: str,
    tlogger: TraceLogger,
) -> tuple[UniversalCompletion, BaseModel]:

    try:
        openai_response = openai_helper.openai_parse_request(
            input=openai_input,
            text_format=model,
            max_output_tokens=max_output_tokens,
            tag=tag,
            tlogger=tlogger,
        )
        return UniversalCompletion.from_openai_response(openai_response), model.model_validate_json(openai_response.output_text)
    except Exception as e:
        tlogger.error(e)
        raise

    try:
        yandex_response, parsed = yandex_gpt_helper.parse_completion(
            messages=[yandex_gpt_helper.openai_input_message_to_yandex_gpt_message(msg) for msg in openai_input],
            model=model,
            max_tokens=max_output_tokens,
            tag=tag,
            tlogger=tlogger,
        )

        return UniversalCompletion.from_yandex_gpt_reponse(yandex_response), parsed
    except:
        raise


def create_completion(
    openai_input: list[ResponseInputItemParam],
    text_format: ResponseTextConfigParam | None = None,
    max_output_tokens: int = 2000,
    *,
    tag: str,
    tlogger: TraceLogger,
) -> UniversalCompletion:

    try:
        openai_response = openai_helper.openai_request(
            input=openai_input,
            text=text_format or NOT_GIVEN,
            max_output_tokens=max_output_tokens,
            tag=tag,
            tlogger=tlogger,
        )

        return UniversalCompletion.from_openai_response(openai_response)
    except Exception as e:
        tlogger.error(e)
        raise

    try:
        yandex_response = yandex_gpt_helper.create_completion(
            messages=[yandex_gpt_helper.openai_input_message_to_yandex_gpt_message(msg) for msg in openai_input],
            schema=text_format.get("format", {}).get("schema") if text_format else None,
            max_tokens=max_output_tokens,
            tag=tag,
            tlogger=tlogger,
        )

        return UniversalCompletion.from_yandex_gpt_reponse(yandex_response)
    except:
        raise
