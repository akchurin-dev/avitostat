import json
from typing import Iterable
from typing import NamedTuple

from openai.types.responses import ResponseInputItemParam
from openai.types.responses import ResponseTextConfigParam

import amo.models
from amo.utils.ai.answers import get_dialog_str
from utils import ai_helper
from utils.logging import TraceLogger


SYSTEM_PROMPT = """
Тебе передаются типы обращений клиентов, описания типов и чат с клиентом. Твоя задача - определить диалог в какой-то из типов.
Есть вариант \"Другое\", его выбирай только, если остальные варианты никак не подходят.
"""


class CaseTypeBasedDecision(NamedTuple):
    standart_pipeline: bool = False
    ignore: bool = False

    pipeline_id: int = 0
    pipeline_status_id: int = 0


def define_dialog_case(
    task: amo.models.AmoChatBotTask,
    messages: list[ResponseInputItemParam],
    *,
    tlogger: TraceLogger,
) -> CaseTypeBasedDecision:

    assert task.chatbot is not None
    cases = amo.models.AmoCaseType.get_by_chatbot(task.chatbot.pk)

    if len(cases) == 0:
        return CaseTypeBasedDecision(standart_pipeline=True)

    response = ai_helper.create_completion(
        openai_input=_get_openai_input(cases, messages),
        text_format=_get_answer_format(cases),
        tag=f"Amo | {task.account.domain} | dialog case type definition",
        tlogger=tlogger,
    )

    case_title: str = json.loads(response.answer_text)["case"]
    chooced_case = [c for c in cases if c.title == case_title][0]

    if chooced_case.handling_way == amo.models.AmoCaseType.HandlingWay.DEFAULT_PIPELINE:
        return CaseTypeBasedDecision(standart_pipeline=True)

    if chooced_case.handling_way == amo.models.AmoCaseType.HandlingWay.IGNORE:
        return CaseTypeBasedDecision(ignore=True)

    assert chooced_case.pipeline_status is not None
    return CaseTypeBasedDecision(
        pipeline_id=chooced_case.pipeline_status.pipeline_id,
        pipeline_status_id=chooced_case.pipeline_status.amo_id,
    )


def _get_openai_input(cases: Iterable[amo.models.AmoCaseType], messages: list[ResponseInputItemParam]) -> list[ResponseInputItemParam]:
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": "\n".join([
                "Возможные типы обращений:",
                "",
                "\n\n".join([
                    f"{c.title}{(':\n' + c.description) if c.description else ';'}" for c in cases
                ]),
                "",
                "",
                "Чат с клиентом:",
                get_dialog_str(messages),
            ]),
        },
    ]


def _get_answer_format(cases: Iterable[amo.models.AmoCaseType]) -> ResponseTextConfigParam:
    return {
        "format": {
            "type": "json_schema",
            "name": "suitable_dialog_case",
            "schema": {
                "type": "object",
                "properties": {
                    "case": {
                        "type": "string",
                        "enum": [c.title for c in cases] + ["Другое"],
                    },
                    "explanation": {
                        "type": "string",
                    },
                },
                "additionalProperties": False,
                "required": ["case", "explanation"],
            },
        },
    }
