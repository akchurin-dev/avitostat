import json

from openai.types.responses.response_input_param import ResponseInputParam
from openai.types.responses.response_input_param import ResponseInputItemParam
from openai.types.responses.response_text_config_param import ResponseTextConfigParam

import amo.models
from amo.utils import amo_api
from amo.utils import amo_fields
from amo.utils.ai import answers
from utils.logging import TraceLogger


def check_fields_isolately_and_update_ai_result(
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    ai_answer: answers.AIAnswer,
    tlogger: TraceLogger,
) -> None:

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

    for fillable_field, amo_field in fillable_field_amo_field_pairs:
        value = find_value(chatbot, messages, fillable_field, amo_field, tlogger=tlogger)

        if not value or value in amo_fields.ENUM_EMPTY_VALUES:
            continue

        if fillable_field.entity == amo.models.AmoEntity.CONTACT:
            if ai_answer.payload.contacts is None:
                ai_answer.payload.contacts = {}
            ai_answer.payload.contacts[fillable_field.name] = value
        else:
            if ai_answer.payload.lead_info is None:
                ai_answer.payload.lead_info = {}
            ai_answer.payload.lead_info[fillable_field.name] = value


def find_value(
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    fillable_field: amo.models.FillableField,
    amo_field: amo_api.Field | None,
    *,
    tlogger: TraceLogger,
):
    response = answers.openai_request_with_retries(
        input=get_ai_input(chatbot, messages, fillable_field),
        text=get_text_format(fillable_field, amo_field),
        tlogger=tlogger,
    )
    struct = json.loads(response.output_text)

    tlogger.info({"isolated field checked": {
        "field": fillable_field.name,
        "value": struct[fillable_field.name],
    }})

    return struct[fillable_field.name]


def get_ai_input(
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


def get_text_format(fillable_field: amo.models.FillableField, amo_field: amo_api.Field | None) -> ResponseTextConfigParam:
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
