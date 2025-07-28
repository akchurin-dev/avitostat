import json
from typing import NamedTuple
from typing import TypedDict

from openai.types.responses import ResponseInputParam
from openai.types.responses import ResponseInputItemParam
from openai.types.responses import ResponseTextConfigParam

import amo.models
from amo.utils import amo_api
from amo.utils.ai.answers import get_fillable_entity_schema
from amo.utils.ai.openai import openai_request_with_retries
from utils.logging import TraceLogger


SYSTEM_PROMPT = """
Ты — анализатор переписки. Получаешь текст диалога и список нужных полей.
Твоя задача — найти и заполнить эти поля по переписке.
- Используй прямую и косвенную информацию.
- Если поле не указано — внеси туда null.
- Не придумывай данных, но делай логические выводы (например, имя из email).
- Отвечай только значениями полей, без пояснений.
"""


class EntitiesFieldsValues(TypedDict):
    contact: dict[str, str | list[str] | None] | None
    lead: dict[str, str | list[str] | None] | None


class AIAnswer(NamedTuple):
    entities_info: EntitiesFieldsValues
    tokens_prompt: int
    tokens_completion: int


def recognize_fields(
    account: amo.models.AmoAccount,
    messages: list[ResponseInputItemParam],
    fillable_fields: list[amo.models.FillableField],
    *,
    tlogger: TraceLogger,
) -> AIAnswer:

    response = openai_request_with_retries(
        input=_get_ai_input(messages, fillable_fields),
        text=_get_text_format(account, fillable_fields, tlogger=tlogger),
        tag=f"Amo | {account.name} | recognize fields",
        tlogger=tlogger,
    )

    tokens_prompt = tokens_completion = 0
    if response.usage:
        tokens_prompt = response.usage.input_tokens
        tokens_completion = response.usage.output_tokens

    return AIAnswer(
        entities_info=json.loads(response.output_text),
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
    )


def _get_ai_input(messages: list[ResponseInputItemParam], fillable_fields: list[amo.models.FillableField]) -> ResponseInputParam:
    ai_input: ResponseInputParam = [{"role": "system", "content": SYSTEM_PROMPT}]

    ai_input.append({
        "role": "user",
        "content": (
            "Поля которые нужно распознать:\n" + _get_fillable_fields_str(fillable_fields)
            + "\n\n\n"
            + "Чат с клиентом:\n" + _get_dialog_str(messages)
        ),
    })

    return ai_input


def _get_text_format(
    account: amo.models.AmoAccount,
    fillable_fields: list[amo.models.FillableField],
    *,
    tlogger: TraceLogger,
) -> ResponseTextConfigParam:

    text_format: ResponseTextConfigParam = {"format": {
        "type": "json_schema",
        "name": "recognized_fields",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "contact": get_fillable_entity_schema(account, fillable_fields, amo_api.EntityEnum.CONTACTS, tlogger=tlogger),
                "lead": get_fillable_entity_schema(account, fillable_fields, amo_api.EntityEnum.LEADS, tlogger=tlogger),
            },
            "additionalProperties": False,
            "required": ["contact", "lead"],
        },
    }}

    return text_format


def _get_dialog_str(messages: list[ResponseInputItemParam]) -> str:
    replics: list[str] = []

    for msg in messages:
        if "role" not in msg or "content" not in msg:
            continue

        author = {"assistant": "Менеджер", "user": "Клиент"}.get(msg["role"])
        if author is None:
            continue

        text = "<Не текстовое сообщение>"
        if isinstance(msg["content"], str):
            text = msg["content"]

        replics.append(author + ": " + text)

    return "\n\n".join(replics)


def _get_fillable_fields_str(fillable_fields: list[amo.models.FillableField]) -> str:
    parts: list[str] = []

    for fillable_field in fillable_fields:
        lines = [
            "- Название: " + fillable_field.name,
            "  Относится к: " + fillable_field.entity,
        ]

        if fillable_field.description:
            lines.append("  Описание: " + fillable_field.description)

        parts.append("\n".join(lines))

    return "\n\n".join(parts)
