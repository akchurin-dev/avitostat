import datetime
import re
import time
from typing import Iterable

from openai.types.responses import ResponseInputParam
from openai.types.responses import ResponseTextConfigParam
from openai.types.responses.easy_input_message_param import EasyInputMessageParam as GPTMessage
import pydantic
from pydantic import BaseModel

from ai_requests import ai_requests
import amo.models
from amo.utils import amo_api
from amo.utils import amo_fields
from amo.utils.amo_messages import Message
from amo.utils.amo_messages import MessageTypeEnum
from amo.utils.amo_transcriptions import TranscriptionsForMessages
from chat_bot.ai_utils import client
from chat_bot.ai_utils import MODEL
from chat_bot.ai_utils import use_gpt_flag
from utils.logging import TraceLogger


AI_RETRIES = 3
PHRASE_AUTHOR_REGEX = re.compile(r"^\s*\w+:\s*")


class AIAnswerPayload(BaseModel):
    answer: str
    contacts: dict[str, str | None] | None = None
    lead_info: dict[str, str | None] | None = None
    new_status: str | None = None


class AIAnswer(BaseModel):
    payload: AIAnswerPayload
    tokens_completion: int = 0
    tokens_prompt: int = 0


def generate_answer(
    chatbot: amo.models.AmoChatBot,
    messages: list[Message],
    transcriptions: TranscriptionsForMessages,
    account: amo.models.AmoAccount,
    lead_id: int | str,
    *,
    tlogger: TraceLogger,
) -> AIAnswer:

    if not use_gpt_flag():
        return AIAnswer(payload=AIAnswerPayload(answer="mock answer"))

    fillable_fields = amo.models.FillableField.objects.filter(chatbot=chatbot)

    lead = amo_api.get_lead(
        domain=account.domain,
        lead_id=lead_id,
        tlogger=tlogger,
    )
    available_pipeline_statuses = amo_api.get_pipeline_statuses(
        domain=account.domain,
        pipeline_id=lead.pipeline_id,
        tlogger=tlogger,
    )

    gpt_messages = _get_gpt_messages(
        chatbot=chatbot,
        messages=messages,
        transcriptions=transcriptions,
        fillable_fields=fillable_fields,
        available_pipeline_statuses=available_pipeline_statuses,
        lead=lead,
    )

    text_format = _get_text_format(
        account=account,
        fields=fillable_fields,
        available_pipeline_statuses=available_pipeline_statuses,
        field_for_new_status=not chatbot.change_status_only_when_qualification,
        tlogger=tlogger,
    )

    error = None

    for _ in range(AI_RETRIES):
        try:
            response = client.responses.create(
                model=MODEL,
                input=gpt_messages,
                text=text_format,
                max_output_tokens=2000,
            )
            ai_requests.create_from_response(response, tlogger=tlogger)

            payload = AIAnswerPayload.model_validate_json(response.output_text)

            break
        except pydantic.ValidationError as e:
            error = e
            tlogger.info({
                "title": "Invalid gpt response",
                "error": e,
            })
    else:
        if error:
            raise error

    tokens_completion = tokens_prompt = 0

    if response.usage:
        tokens_completion = response.usage.output_tokens
        tokens_prompt = response.usage.input_tokens

    res = AIAnswer(
        payload=payload,
        tokens_completion=tokens_completion,
        tokens_prompt=tokens_prompt,
    )
    res.payload.answer = _delete_phrase_author_if_exists(res.payload.answer, tlogger=tlogger)

    return res


def _get_gpt_messages(
    chatbot: amo.models.AmoChatBot,
    messages: list[Message],
    transcriptions: TranscriptionsForMessages,
    fillable_fields: Iterable[amo.models.FillableField],
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    lead: amo_api.Lead,
) -> ResponseInputParam:

    current_status = None

    for status in available_pipeline_statuses:
        if status.id == lead.status_id:
            current_status = status
            break

    if current_status is None:
        raise Exception(f"Status (id={lead.status_id}) not found in pipeline (id={lead.pipeline_id})")

    prompt = _get_prompt(chatbot, fillable_fields, available_pipeline_statuses, current_status)

    gpt_messages: ResponseInputParam = [{"role": "system", "content": prompt}]

    if chatbot.duplicate_instructions:
        gpt_messages.append({"role": "user", "content": chatbot.duplicate_instructions})

    gpt_messages.extend([_amo_message_to_gpt_format(message, transcriptions) for message in messages])

    return gpt_messages


def _amo_message_to_gpt_format(message: Message, transcriptions: TranscriptionsForMessages) -> GPTMessage:
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


def _get_text_format(
    account: amo.models.AmoAccount,
    fields: Iterable[amo.models.FillableField],
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    field_for_new_status: bool,
    *,
    tlogger: TraceLogger,
) -> ResponseTextConfigParam:

    contacts_schema = _get_fillable_entity_schema(
        account=account,
        fields=fields,
        entity=amo_api.EntityEnum.CONTACTS,
        tlogger=tlogger,
    )

    lead_schema = _get_fillable_entity_schema(
        account=account,
        fields=fields,
        entity=amo_api.EntityEnum.LEADS,
        tlogger=tlogger,
    )

    properties: dict = {
        "answer": {"type": "string"},
    }

    if contacts_schema:
        properties["contacts"] = contacts_schema

    if lead_schema:
        properties["lead_info"] = lead_schema

    if field_for_new_status:
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

    all_fields = amo_api.get_fields(
        domain=account.domain,
        entity=entity,
        tlogger=tlogger,
    )

    fillable_fields: list[tuple[amo_api.Field, amo.models.FillableField]] = []

    for field in fields:
        if entity == amo_api.EntityEnum.LEADS and field.entity != amo.models.AmoEntity.LEAD.value:
            continue

        if entity == amo_api.EntityEnum.CONTACTS and field.entity != amo.models.AmoEntity.CONTACT.value:
            continue

        amo_field = amo_fields.find_text_field(field.name, all_fields, tlogger=tlogger)

        if amo_field:
            fillable_fields.append((amo_field, field))

    if len(fillable_fields) == 0:
        return None

    properties = {
        amo_field.name: _get_field_schema(amo_field, fillable_field.description)
            for amo_field, fillable_field in fillable_fields
    }

    return {
        "type": ["object", "null"],
        "properties": properties,
        "required": list(properties.keys()),
        "additionalProperties": False,
    }


def _get_field_schema(field: amo_api.Field, description: str) -> dict:
    schema = {
        "type": ["string", "null"],
        "description": description,
    }

    if field.type in amo_fields.ENUM_TYPES:
        assert field.enums is not None
        schema["enum"] = [field_enum.value for field_enum in field.enums]

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


def _dialog_to_str(dialog: list[Message]) -> str:
    lines = ["Чат с клиентом:"]

    for message in dialog:
        author = "Клиент" if message.incoming else "Менеджер"
        lines.append(f"{author}: {message.text}")

    return "\n".join(lines)


def _get_prompt(
    chatbot: amo.models.AmoChatBot,
    fields: Iterable[amo.models.FillableField],
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    current_status: amo_api.PipelineStatus,
) -> str:

    prompt = ""
    prompt = _add_chatbot_prompt(prompt, chatbot)
    prompt = _add_fields_prompt(prompt, fields)

    if chatbot.change_status_only_when_qualification:
        prompt = _add_pipelines_prompt(
            prompt=prompt,
            pipeline_status_update_rules=chatbot.pipeline_status_update_rules,
            available_pipeline_statuses=available_pipeline_statuses,
            current_status=current_status,
        )

    return prompt


def _add_chatbot_prompt(prompt: str, chatbot: amo.models.AmoChatBot) -> str:
    role_and_tasks_title = "Твои роль и задачи"
    behaviour_style_title = "Стиль поведения во время общения"
    company_and_products_title = "Описание компании и ее продуктов"
    important_conditions_title = "Важные условия на которые тебе нужно обратить внимание"
    links_and_contacts_title = "Полезные ссылки и контакты"

    titles_and_descriptions = {
        role_and_tasks_title: chatbot.role_and_tasks,
        behaviour_style_title: chatbot.behaviour_style,
        company_and_products_title: chatbot.company_and_products,
        important_conditions_title: chatbot.important_conditions,
        links_and_contacts_title: chatbot.links_and_contacts,
    }

    titles_ordered = [
        role_and_tasks_title,
        behaviour_style_title,
        company_and_products_title,
        important_conditions_title,
        links_and_contacts_title,
    ]

    new_text = "\n\n".join([title + "\n" + desc for title in titles_ordered if (desc := titles_and_descriptions[title])])

    if not new_text:
        return prompt

    if prompt:
        prompt += "\n\n"

    return prompt + new_text


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
