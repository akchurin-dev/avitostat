from __future__ import annotations

from datetime import date
from datetime import datetime
from enum import Enum
from typing import Literal
from typing import TypedDict

import httpx
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from base import settings
from utils import httpx_helper
from utils.logging import TraceLogger


MessageRole = Literal["system", "assistant", "user"]


class ReasoningMode(Enum):
    REASONING_MODE_UNSPECIFIED = "REASONING_MODE_UNSPECIFIED"
    DISABLED = "DISABLED"
    ENABLED_HIDDEN = "ENABLED_HIDDEN"


class YandexGPTMessage(TypedDict):
    role: MessageRole
    text: str


class Usage(BaseModel):
    completion_tokens: int = Field(alias="completionTokens")
    completion_tokens_details: dict = Field(alias="completionTokensDetails")
    input_text_tokens: int = Field(alias="inputTextTokens")
    total_tokens: int = Field(alias="totalTokens")


class CompletionResult(BaseModel):
    alternatives: list[CompletionResult_Alternative]
    model_version: date = Field(alias="modelVersion")
    usage: Usage

    @field_validator("model_version", mode="before")
    def validate_model_version(cls, v: str) -> date:
        return datetime.strptime(v, "%d.%m.%Y").date()


class CompletionResult_Alternative(BaseModel):
    message: CompletionResult_Alternative_Message
    status: str


class CompletionResult_Alternative_Message(BaseModel):
    role: MessageRole
    text: str


client = httpx.Client(
    base_url="https://llm.api.cloud.yandex.net",
    headers={
        "Authorization": "Api-Key " + settings.YANDEX_GPT_API_KEY,
    },
    timeout=1,
)


def create_completion(
    model_uri: str,
    messages: list[YandexGPTMessage],
    schema: dict | None = None,
    reasoning_mode: ReasoningMode = ReasoningMode.DISABLED,
    temperature: float = 0.6,
    max_tokens: int = 2000,
    *,
    tlogger: TraceLogger,
) -> CompletionResult:
    """ https://yandex.cloud/ru/docs/ai-studio/text-generation/api-ref/TextGeneration/completion """

    action = "/foundationModels/v1/completion"

    body = {
        "modelUri": model_uri,
        "completionOptions": {
            "stream": False,
            "temperature": temperature,
            "maxTokens": max_tokens,
            "reasoningOptions": {
                "mode": reasoning_mode.value,
            },
        },
        "messages": messages,
    }

    if schema is not None:
        body["jsonSchema"] = {
            "schema": schema,
        }

    response = httpx_helper.request(
        method="POST",
        url=action,
        json=body,
        client=client,
        tlogger=tlogger,
    )

    res_data = None
    if response.content:
        res_data = response.json()

    response.raise_for_status()
    assert res_data is not None

    return CompletionResult.model_validate(res_data["result"])
