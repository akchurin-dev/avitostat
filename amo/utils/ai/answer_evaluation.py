from openai.types.responses import ResponseInputItemParam
from pydantic import BaseModel
from pydantic import Field

import amo.models
from utils import ai_helper
from utils import universal_messages
from utils.logging import TraceLogger


SYSTEM_PROMPT = """
Ты — эксперт по оценке качества ответов менеджера.
Тебе передают чат с клиентом и требования, которым должны соответствовать ответы менеджера.
Дай оценку ПОСЛЕДНЕМУ сообщению менеджера.
"""


class Evaluation(BaseModel):
    rate: int = Field(description="Оценка от 1 до 5")
    explanation: str


def evaluate_answer(
    account: amo.models.AmoAccount,
    messages: list[universal_messages.Message],
    requirements: str,
    from_sandbox: bool = False,
    *,
    tlogger: TraceLogger,
) -> Evaluation:

    tag = f"Amo | {account.domain} | answer evaluation"
    if from_sandbox:
        tag += f" [sandbox]"

    _, answer = ai_helper.parse_completion(
        openai_input=_get_ai_input(messages, requirements),
        model=Evaluation,
        tag=tag,
        tlogger=tlogger,
    )

    assert isinstance(answer, Evaluation)
    return answer


def _get_ai_input(messages: list[universal_messages.Message], requirements: str) -> list[ResponseInputItemParam]:
    system_message = "\n".join([
        SYSTEM_PROMPT,
        "\n\n\n",
        "<Requirements>\n" + requirements + "\n</Requirements>",
        "\n\n\n",
        universal_messages.dialog_as_xml(messages),
    ])

    return [
        {
            "role": "system",
            "content": system_message,
        },
        *universal_messages.dialog_to_openai_images(messages),
    ]
