import json
from typing import Any
from typing import NamedTuple

from openai.types.responses.response_input_param import ResponseInputParam
from openai.types.responses.response_input_param import ResponseInputItemParam
from openai.types.responses.response_text_config_param import ResponseTextConfigParam

import amo.models
from amo.utils import amo_api
from amo.utils import amo_fields
from amo.utils.ai import answers, fields_recognition
from utils import yandex_gpt_helper
from utils.logging import TraceLogger
# from utils.openai_helper import openai_request


class TokensUsage(NamedTuple):
    tokens_prompt: int
    tokens_completion: int


def check_fields_isolately_and_update_ai_result(
    account: amo.models.AmoAccount,
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    ai_answer: fields_recognition.AIAnswer,
    tlogger: TraceLogger,
) -> TokensUsage:

    fillable_fields = amo.models.FillableField.objects.filter(chatbot=chatbot, isolated_check=True)
    fillable_field_amo_field_pairs = answers.get_fillable_field_amo_field_pairs(
        chatbot.account,
        fillable_fields,
        amo_api.EntityEnum.CONTACTS,
        tlogger=tlogger,
    )
    fillable_field_amo_field_pairs.extend(answers.get_fillable_field_amo_field_pairs(
        chatbot.account,
        fillable_fields,
        amo_api.EntityEnum.LEADS,
        tlogger=tlogger,
    ))

    tlogger.info({"fields for isolated check": [ff.name for ff in fillable_fields]})

    tokens_prompt = tokens_completion = 0

    for fillable_field, amo_field in fillable_field_amo_field_pairs:
        value, usage = find_value(account, chatbot, messages, fillable_field, amo_field, tlogger=tlogger)

        tokens_prompt += usage.tokens_prompt
        tokens_completion += usage.tokens_completion

        if not value or value in amo_fields.ENUM_EMPTY_VALUES:
            continue

        if fillable_field.entity == amo.models.AmoEntity.CONTACT:
            if ai_answer.entities_info["contact"] is None:
                ai_answer.entities_info["contact"] = {}

            if ai_answer.entities_info["contact"] is not None:
                ai_answer.entities_info["contact"][fillable_field.name] = value
        else:
            if ai_answer.entities_info["lead"] is None:
                ai_answer.entities_info["lead"] = {}

            if ai_answer.entities_info["lead"] is not None:
                ai_answer.entities_info["lead"][fillable_field.name] = value

    return TokensUsage(tokens_prompt, tokens_completion)


def find_value(
    account: amo.models.AmoAccount,
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    fillable_field: amo.models.FillableField,
    amo_field: amo.models.AmoField | None,
    *,
    tlogger: TraceLogger,
) -> tuple[Any, TokensUsage]:

    # response = openai_request(
    #     input=get_ai_input(chatbot, messages, fillable_field),
    #     text=get_text_format(fillable_field, amo_field),
    #     tag=f"Amo | {account.domain} | field isolated check",
    #     tlogger=tlogger,
    # )
    # struct = json.loads(response.output_text)

    # tlogger.info({"isolated field checked": {
    #     "field": fillable_field.name,
    #     "value": struct[fillable_field.name],
    # }})

    # usage = TokensUsage(0, 0)
    # if response.usage:
    #     usage = TokensUsage(response.usage.input_tokens, response.usage.output_tokens)

    # return struct[fillable_field.name], usage

    response = yandex_gpt_helper.create_completion(
        messages=get_yandex_gpt_input(chatbot, messages, fillable_field),
        schema=get_text_format(fillable_field, amo_field)["format"]["schema"],
        tag=f"Amo | {account.domain} | field isolated check",
        tlogger=tlogger,
    )
    struct = json.loads(response.alternatives[0].message.text)

    tlogger.info({"isolated field checked": {
        "field": fillable_field.name,
        "value": struct[fillable_field.name],
    }})

    usage = TokensUsage(response.usage.input_text_tokens, response.usage.completion_tokens)

    return struct[fillable_field.name], usage


def get_openai_input(
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    fillable_field: amo.models.FillableField,
) -> ResponseInputParam:

    prompt = "\n".join([
        "Ты консультируешь клиентов в чате магазина. Ниже информация о магазине.",
        chatbot.company_and_products,
        "",
        f"Твоя задача - проанализировать переписку с клиентом и выяснить значения поля '{fillable_field.name}'.",
        "Ниже информация о поле.",
        fillable_field.description or "<Дополнительная информация отсутствует>",
        "",
        "Не додумывай, исходи строго из содержимого чата с клиентом. Если в чате недостаточно информации, то оставь поле путым (null или None)",
    ])
    ai_input: ResponseInputParam = [{"role": "system", "content": prompt}]
    ai_input.extend(messages)

    return ai_input


def get_yandex_gpt_input(
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    fillable_field: amo.models.FillableField,
):
    openai_input = get_openai_input(chatbot, messages, fillable_field)
    yandex_gpt_input = [yandex_gpt_helper.openai_input_message_to_yandex_gpt_message(msg) for msg in openai_input]

    return yandex_gpt_input


def get_text_format(fillable_field: amo.models.FillableField, amo_field: amo.models.AmoField | None) -> ResponseTextConfigParam:
    return {
        "format": {
            "type": "json_schema",
            "name": "field_wrapper",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    fillable_field.name: answers.get_field_schema(amo_field, fillable_field),
                },
                "required": [fillable_field.name],
                "additionalProperties": False,
            },
        }
    }
