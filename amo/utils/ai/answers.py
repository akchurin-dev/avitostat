import re
from typing import Iterable

import pydantic
from openai.types.responses import Response
from openai.types.responses import ResponseInputParam
from openai.types.responses import ResponseInputItemParam
from openai.types.responses import ResponseTextConfigParam
from pydantic import BaseModel

import amo.models
from ai_requests import ai_requests
from amo.utils import amo_api
from amo.utils import amo_fields
from amo.utils import amo_leads
from amo.utils.amo_messages import Message
from amo.utils.amo_messages import MessageTypeEnum
from amo.utils.amo_transcriptions import TranscriptionsForMessages
from chat_bot.ai_utils import client
from chat_bot.ai_utils import MODEL
from chat_bot.ai_utils import use_gpt_flag
from prompts import prompts
from utils.logging import TraceLogger


AI_RETRIES = 3
PHRASE_AUTHOR_REGEX = re.compile(r"^\s*\w+:\s*")


class AIAnswerPayload(BaseModel):
    answer: str | None = None
    contacts: dict[str, str | None] | None = None
    lead_info: dict[str, str | None] | None = None
    new_status: str | None = None


class AIAnswer(BaseModel):
    payload: AIAnswerPayload
    tokens_completion: int = 0
    tokens_prompt: int = 0


def generate_answer(
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    account: amo.models.AmoAccount,
    lead_id: int,
    *,
    tlogger: TraceLogger,
) -> AIAnswer:

    if not use_gpt_flag():
        return AIAnswer(payload=AIAnswerPayload(answer="mock answer"))

    lead, contact = amo_leads.get_lead_contact_pair(chatbot.account, lead_id, tlogger=tlogger)
    all_fillable_fields = amo.models.FillableField.objects.filter(chatbot=chatbot, isolated_check=False)
    unknown_fillable_fields = get_unknown_fillable_fields(account, all_fillable_fields, lead, contact, tlogger=tlogger)
    available_pipeline_statuses = amo_api.get_pipeline_statuses(account, lead.pipeline_id, tlogger=tlogger)

    gpt_messages = _get_gpt_messages(
        account=account,
        chatbot=chatbot,
        messages=messages,
        all_fillable_fields=all_fillable_fields,
        unknown_fillable_fields=unknown_fillable_fields,
        available_pipeline_statuses=available_pipeline_statuses,
        lead=lead,
        contact=contact,
        tlogger=tlogger,
    )

    text_format = get_text_format(
        chatbot=chatbot,
        fields=unknown_fillable_fields,
        field_for_answer=True,
        available_pipeline_statuses=available_pipeline_statuses,
        tlogger=tlogger,
    )

    response = openai_request_with_retries(
        input=gpt_messages,
        text=text_format,
        tag=f"Amo | {account.domain} | generate answer",
        tlogger=tlogger,
    )
    payload = AIAnswerPayload.model_validate_json(response.output_text)

    return get_ai_answer_wrapper(response, payload, tlogger=tlogger)


def parse_form(account: amo.models.AmoAccount, chatbot: amo.models.AmoChatBot, form: str, *, tlogger: TraceLogger) -> AIAnswer:
    if not use_gpt_flag():
        return AIAnswer.model_validate({})

    fillable_fields = amo.models.FillableField.objects.filter(chatbot=chatbot)

    gpt_messages: ResponseInputParam = [
        {"role": "system", "content": "Extract required fields from text"},
        {"role": "user", "content": "Extract required fields from this text:\n\n" + form},
    ]

    text_format = get_text_format(
        chatbot=chatbot,
        fields=fillable_fields,
        field_for_answer=False,
        available_pipeline_statuses=[],
        tlogger=tlogger,
    )

    response = openai_request_with_retries(
        input=gpt_messages,
        text=text_format,
        tag=f"Amo | {account.domain} | parse form",
        tlogger=tlogger,
    )
    payload = AIAnswerPayload.model_validate_json(response.output_text)

    return get_ai_answer_wrapper(response, payload, tlogger=tlogger)


def openai_request_with_retries(
    input: ResponseInputParam,
    text: ResponseTextConfigParam,
    max_output_tokens: int = 2000,
    *,
    tag: str,
    tlogger: TraceLogger,
) -> Response:

    error = None

    for _ in range(AI_RETRIES):
        try:
            response = client.responses.create(
                model=MODEL,
                input=input,
                text=text,
                max_output_tokens=max_output_tokens,
            )
            ai_requests.create_from_response(tag, response, tlogger=tlogger)
            return response
        except pydantic.ValidationError as e:
            error = e
            tlogger.info({
                "title": "Invalid gpt response",
                "error": e,
            })

    assert error
    raise error


def _get_gpt_messages(
    account: amo.models.AmoAccount,
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    all_fillable_fields: Iterable[amo.models.FillableField],
    unknown_fillable_fields: Iterable[amo.models.FillableField],
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    lead: amo_api.Lead,
    contact: amo_api.Contact,
    *,
    tlogger: TraceLogger,
) -> ResponseInputParam:

    current_status = None

    for status in available_pipeline_statuses:
        if status.id == lead.status_id:
            current_status = status
            break

    if current_status is None:
        raise Exception(f"Status (id={lead.status_id}) not found in pipeline (id={lead.pipeline_id})")

    prompt = _get_prompt(account, chatbot, messages, unknown_fillable_fields, available_pipeline_statuses, current_status, tlogger=tlogger)

    gpt_messages: ResponseInputParam = [{"role": "system", "content": prompt}]

    if chatbot.duplicate_instructions:
        gpt_messages.append({"role": "user", "content": chatbot.duplicate_instructions})

    lead_contact_info = known_lead_contact_info(all_fillable_fields, lead, contact)
    if lead_contact_info:
        gpt_messages.append({"role": "user", "content": lead_contact_info})

    gpt_messages.extend(messages)

    return gpt_messages


def known_lead_contact_info(
    fillable_fields: Iterable[amo.models.FillableField],
    lead: amo_api.Lead,
    contact: amo_api.Contact,
) -> str | None:

    known_lead_fields = amo_fields.get_filled_fields(lead)
    known_contact_fields = amo_fields.get_filled_fields(contact)

    fillable_fieds_names_descriptions = {field.name: field.description for field in fillable_fields}

    known_lead_fields = [field for field in known_lead_fields if field.field_name in fillable_fieds_names_descriptions]
    known_contact_fields = [field for field in known_contact_fields if field.field_name in fillable_fieds_names_descriptions]

    if len(known_lead_fields) + len(known_contact_fields) == 0:
        return None

    paragraphs = ["О сделке и о контакте уже известна некоторая информация. Не спращивай о том, что уже извество."]

    if known_lead_fields:
        paragraphs.append(_get_entity_info_str("Информация о сделке", known_lead_fields, fillable_fieds_names_descriptions))

    if known_contact_fields:
        paragraphs.append(_get_entity_info_str("Информация о контакте", known_contact_fields, fillable_fieds_names_descriptions))

    return "\n\n".join(paragraphs)


def _get_entity_info_str(
    title: str,
    known_fields: list[amo_api.CustomFieldValue],
    fillable_fields_names_descriptions: dict[str, str],
) -> str:

    assert known_fields

    lines = [title]

    for field_value in known_fields:
        line = ["-", field_value.field_name]

        description = fillable_fields_names_descriptions.get(field_value.field_name)
        if description:
            line.append("(" + description + ")")

        line.extend(["=", str(field_value.values[0].value)])

        lines.append(" ".join(line))

    return "\n".join(lines)


def amo_message_to_gpt_format(message: Message, transcriptions: TranscriptionsForMessages) -> ResponseInputItemParam:
    role = "assistant"
    if message.incoming:
        role = "user"

    if message.type == MessageTypeEnum.TEXT:
        assert message.text
        return {
            "role": role,
            "content": message.text,
        }

    if message.type == MessageTypeEnum.PICTURE:
        assert message.file_url
        return {
            "role": role,
            "content": [{
                "type": "input_image",
                "image_url": message.file_url,
                "detail": "low",
            }],
        }

    if message.type == MessageTypeEnum.VOICE:
        return {
            "role": role,
            "content": transcriptions.get_transcription(message),
        }

    raise Exception(f"Unknown message type, got {message.type}")


def get_text_format(
    chatbot: amo.models.AmoChatBot,
    fields: Iterable[amo.models.FillableField],
    field_for_answer: bool,
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    *,
    tlogger: TraceLogger,
) -> ResponseTextConfigParam:

    contacts_schema = _get_fillable_entity_schema(
        account=chatbot.account,
        fields=fields,
        entity=amo_api.EntityEnum.CONTACTS,
        tlogger=tlogger,
    )

    lead_schema = _get_fillable_entity_schema(
        account=chatbot.account,
        fields=fields,
        entity=amo_api.EntityEnum.LEADS,
        tlogger=tlogger,
    )

    properties: dict = {}

    if field_for_answer:
        properties["answer"] = {"type": "string"}

    if contacts_schema:
        properties["contacts"] = contacts_schema

    if lead_schema:
        properties["lead_info"] = lead_schema

    if len(available_pipeline_statuses) != 0 and not chatbot.change_status_only_when_qualification:
        properties["new_status"] = {
            "type": ["string", "null"],
            "description": "Новый этап сделки. Если сделка не меняет этап, то null",
            "enum": [status.name for status in available_pipeline_statuses],
        }

    schema = {
        "type": "object",
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }

    text_format: ResponseTextConfigParam = {
        "format": {
            "type": "json_schema",
            "name": "chat_answer",
            "schema": schema,
            "strict": True,
        },
    }

    tlogger.info({
        "text_format": text_format,
    })

    return text_format


def _get_fillable_entity_schema(
    account: amo.models.AmoAccount,
    fields: Iterable[amo.models.FillableField],
    entity: amo_api.EntityEnum,
    *,
    tlogger: TraceLogger,
) -> dict | None:

    fillable_field_amo_field_pairs = get_fillable_field_amo_field_pairs(account, fields, entity, tlogger=tlogger)

    if len(fillable_field_amo_field_pairs) == 0:
        return None

    properties = {
        fillable_field.name: get_field_schema(amo_field, fillable_field)
            for fillable_field, amo_field in fillable_field_amo_field_pairs
    }

    return {
        "type": ["object", "null"],
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


def get_fillable_field_amo_field_pairs(
    account: amo.models.AmoAccount,
    fillable_fields: Iterable[amo.models.FillableField],
    entity: amo_api.EntityEnum,
    *,
    tlogger: TraceLogger,
) -> list[tuple[amo.models.FillableField, amo_api.Field | None]]:

    all_amo_fields = amo_api.get_fields(account, entity, tlogger=tlogger)
    fillable_field_amo_field_pairs: list[tuple[amo.models.FillableField, amo_api.Field | None]] = []

    for fillable_field in fillable_fields:
        if entity == amo_api.EntityEnum.LEADS and fillable_field.entity != amo.models.AmoEntity.LEAD.value:
            continue

        if entity == amo_api.EntityEnum.CONTACTS and fillable_field.entity != amo.models.AmoEntity.CONTACT.value:
            continue

        amo_field = amo_fields.find_text_field(fillable_field.name, all_amo_fields, tlogger=tlogger)
        fillable_field_amo_field_pairs.append((fillable_field, amo_field))

    return fillable_field_amo_field_pairs


def get_field_schema(amo_field: amo_api.Field | None, fillable_field: amo.models.FillableField) -> dict:
    schema = {
        "type": ["string", "null"],
        "description": fillable_field.description,
    }

    if amo_field and amo_field.type in amo_fields.ENUM_TYPES:
        assert amo_field.enums is not None

        enum_values = [
            field_enum.value
            for field_enum in amo_field.enums
            if field_enum.value not in amo_fields.ENUM_EMPTY_VALUES
        ]

        # if len(enum_values) < 2:
        #     enum_values.extend(["__null__", "__None__"])
        enum_values.extend(["__null__", "__None__"])

        schema["enum"] = enum_values

    return schema


def _delete_phrase_author_if_exists(message: str, *, tlogger: TraceLogger) -> str:
    res = PHRASE_AUTHOR_REGEX.search(message)

    if res is None:
        tlogger.info(f"Prefix with phrase author isn't found in '{message}'")
        return message

    length = len(res.group(0))
    new_message = message[length:]

    tlogger.info(f"Found phrase author in '{message}', new variant is '{new_message}'")

    return new_message


def get_unknown_fillable_fields(
    account: amo.models.AmoAccount,
    all_fillable_fields: Iterable[amo.models.FillableField],
    lead: amo_api.Lead,
    contact: amo_api.Contact,
    *,
    tlogger: TraceLogger,
) -> Iterable[amo.models.FillableField]:

    empty_lead_fields = {f.name for f in amo_fields.get_empty_fields(account, lead, tlogger=tlogger)}
    empty_contact_fields = {f.name for f in amo_fields.get_empty_fields(account, contact, tlogger=tlogger)}

    lead_fillable_fields = [ff for ff in all_fillable_fields if ff.entity == amo.models.AmoEntity.LEAD]
    contact_fillable_fields = [ff for ff in all_fillable_fields if ff.entity == amo.models.AmoEntity.CONTACT]

    unknown_fillable_fields = [ff for ff in lead_fillable_fields if ff.name in empty_lead_fields]
    unknown_fillable_fields.extend(ff for ff in contact_fillable_fields if ff.name in empty_contact_fields)

    tlogger.info({"Unknown fillable fields": [ff.name for ff in unknown_fillable_fields]})

    return unknown_fillable_fields


def _get_prompt(
    account: amo.models.AmoAccount,
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    fields: Iterable[amo.models.FillableField],
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    current_status: amo_api.PipelineStatus,
    *,
    tlogger: TraceLogger,
) -> str:

    prompt = ""
    prompt = _add_chatbot_prompt(prompt, account, chatbot, messages, tlogger=tlogger)
    prompt = _add_fields_prompt(prompt, fields)

    if not chatbot.change_status_only_when_qualification:
        prompt = _add_pipelines_prompt(
            prompt=prompt,
            pipeline_status_update_rules=chatbot.pipeline_status_update_rules,
            available_pipeline_statuses=available_pipeline_statuses,
            current_status=current_status,
        )

    return prompt


# def _add_chatbot_prompt(prompt: str, chatbot: amo.models.AmoChatBot) -> str:
#     role_and_tasks_title = "Твои роль и задачи"
#     behaviour_style_title = "Стиль поведения во время общения"
#     company_and_products_title = "Описание компании и ее продуктов"
#     important_conditions_title = "Важные условия на которые тебе нужно обратить внимание"
#     links_and_contacts_title = "Полезные ссылки и контакты"

#     titles_and_descriptions = {
#         role_and_tasks_title: chatbot.role_and_tasks,
#         behaviour_style_title: chatbot.behaviour_style,
#         company_and_products_title: chatbot.company_and_products,
#         important_conditions_title: chatbot.important_conditions,
#         links_and_contacts_title: chatbot.links_and_contacts,
#     }

#     titles_ordered = [
#         role_and_tasks_title,
#         behaviour_style_title,
#         company_and_products_title,
#         important_conditions_title,
#         links_and_contacts_title,
#     ]

#     new_text = "\n\n".join([title + "\n" + desc for title in titles_ordered if (desc := titles_and_descriptions[title])])

#     if not new_text:
#         return prompt

#     if prompt:
#         prompt += "\n\n"

#     return prompt + new_text


def _add_chatbot_prompt(
    prompt: str,
    account: amo.models.AmoAccount,
    chatbot: amo.models.AmoChatBot,
    messages: list[ResponseInputItemParam],
    *,
    tlogger: TraceLogger,
) -> str:

    prompts_qs = amo.models.AmoPrompt.objects.filter(chatbot=chatbot)
    chatbot_prompt = prompts.define_prompt(
        prompts_qs,
        _get_dialog_str(messages),
        module="Amo",
        account_name=account.domain,
        tlogger=tlogger,
    )

    if not chatbot_prompt:
        return prompt

    if prompt:
        prompt += "\n\n"

    return prompt + chatbot_prompt


def _get_dialog_str(messages: list[ResponseInputItemParam]) -> str:
    replics: list[str] = []

    for msg in messages:
        if "role" not in msg or "content" not in msg:
            continue

        author = {"assistant": "Manager", "user": "Customer"}.get(msg["role"])
        if author is None:
            continue

        text = "Не текстовое сообщение"
        if isinstance(msg["content"], str):
            text = msg["content"]

        replics.append(author + ": " + text)

    return "\n\n".join(replics)


def _add_pipelines_prompt(
    prompt: str,
    pipeline_status_update_rules: str,
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    current_status: amo_api.PipelineStatus,
) -> str:

    if not pipeline_status_update_rules:
        return prompt

    new_articles = [
        "Определи нужно ли перевести сделку в новый статус по следующим правилам:",
        pipeline_status_update_rules,
        "Доступные статусы: " + ", ".join([status.name for status in available_pipeline_statuses]),
        f"Сейчас сделка находится в статусе '{current_status.name}'",
    ]

    new_text = "\n\n".join(new_articles)

    if prompt:
        prompt += "\n\n\n"

    return prompt + new_text


def _add_fields_prompt(prompt: str, fields: Iterable[amo.models.FillableField]) -> str:
    if len(list(fields)) == 0:
        return prompt

    new_articles = ["Твоя задача узнать у клиента следующие данные"]

    for field in fields:
        new_articles.append("\n".join([
            "Поле: " + field.name,
            "Описание: " + field.description,
        ]))

    new_text = "\n\n".join(new_articles)

    if prompt:
        prompt += "\n\n\n"

    return prompt + new_text


def get_ai_answer_wrapper(response: Response, payload: AIAnswerPayload, *, tlogger: TraceLogger) -> AIAnswer:
    tokens_completion = tokens_prompt = 0

    if response.usage:
        tokens_completion = response.usage.output_tokens
        tokens_prompt = response.usage.input_tokens

    if payload.answer:
        payload.answer = _delete_phrase_author_if_exists(payload.answer, tlogger=tlogger)

    return AIAnswer(
        payload=payload,
        tokens_completion=tokens_completion,
        tokens_prompt=tokens_prompt,
    )
