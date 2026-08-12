import json
from typing import Iterable
from typing import Literal

from django.db import models
from openai.types.responses.response_text_config_param import ResponseTextConfigParam

from utils import ai_helper
from utils.logging import TraceLogger


class PromptBase(models.Model):
    title = models.CharField(
        verbose_name="Название",
        max_length=255,
        db_index=True,
    )

    description = models.TextField(
        verbose_name="Краткое описание",
        blank=True,
    )

    text = models.TextField(
        verbose_name="Промпт",
    )

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"{self.title} ({self.pk})"


def define_prompt(
    prompts_iterable: Iterable[PromptBase],
    dialog: str,
    *,
    module: Literal["Amo", "Avito"],
    account_name: str,
    tlogger: TraceLogger,
) -> str | None:

    prompts = list(prompts_iterable)

    if len(prompts) == 0:
        tlogger.info("Prompts not found")
        return None

    if len(prompts) == 1:
        tlogger.info(f"Found only one prompt '{prompts[0].title}'")
        return prompt_instance_to_str(prompts[0])

    response_format = _get_ai_response_format(prompts)

    request_prompt = "\n\n\n".join([
        (
            "Ниже представлен чат с клиентом и описания разных промптов. "
            "Подбери только те промпты, которые необходимы для генерации ответа в представленном чате."
        ),
        "\n\n".join(["Описания промптов:"] + [prompt.title + "\n" + prompt.description or "-" for prompt in prompts]),
        "Чат:\n" + dialog,
    ])


    response = ai_helper.create_completion(
        openai_input=[{"role": "system", "content": request_prompt}],
        text_format=response_format,
        tag=f"{module} | {account_name} | define prompt",
        tlogger=tlogger,
    )

    titles = set(json.loads(response.answer_text)["required_prompts"])
    tlogger.info({
        "All prompts": [p.title for p in prompts],
        "Use prompts": titles,
    })

    if len(titles) == 0:
        return None

    return "\n\n".join([prompt_instance_to_str(prompt) for prompt in prompts if prompt.title in titles])


def prompt_instance_to_str(prompt: PromptBase) -> str:
    return prompt.title + "\n" + prompt.text


def _get_ai_response_format(prompts: Iterable[PromptBase]) -> ResponseTextConfigParam:
    return {
        "format": {
            "type": "json_schema",
            "name": "prompt_defining",
            "schema": {
                "type": "object",
                "properties": {
                    "required_prompts": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Prompts that required for answer generation",
                            "enum": [prompt.title for prompt in prompts],
                        },
                    },
                },
                "required": ["required_prompts"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    }
