import datetime
import re
from typing import Iterable

from openai.types.responses import ResponseInputParam
from openai.types.responses import ResponseTextConfigParam
from openai.types.responses.easy_input_message_param import EasyInputMessageParam as GPTMessage
from pydantic import BaseModel

import amo.models
from amo.utils import amo_api
from amo.utils.amo_messages import Message
from amo.utils.amo_messages import MessageTypeEnum
from amo.utils.amo_transcriptions import TranscriptionsForMessages
from chat_bot.ai_utils import client
from chat_bot.ai_utils import MODEL
from chat_bot.ai_utils import use_gpt_flag
from utils.logging import TraceLogger


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
        fields=fillable_fields,
        available_pipeline_statuses=available_pipeline_statuses,
        field_for_new_status=not chatbot.change_status_only_when_qualification,
    )

    response = client.responses.create(
        model=MODEL,
        input=gpt_messages,
        text=text_format,
        max_output_tokens=2000,
    )

    tokens_completion = tokens_prompt = 0

    if response.usage:
        tokens_completion = response.usage.output_tokens
        tokens_prompt = response.usage.input_tokens

    res = AIAnswer(
        payload=AIAnswerPayload.model_validate_json(response.output_text),
        tokens_completion=tokens_completion,
        tokens_prompt=tokens_prompt,
    )
    res.payload.answer = _delete_phrase_author_if_exists(res.payload.answer, tlogger=tlogger)

    return res


def get_example_prompt(chatbot: amo.models.AmoChatBot) -> str:
    messages = [
        Message(
            id="1",
            incoming=True,
            chat_id="1",
            talk_id=1,
            type=MessageTypeEnum.TEXT,
            text="Привет, хочу купить велосипед",
            file_url=None,
            created_at=datetime.datetime.now(),
        ),
        Message(
            id="2",
            incoming=False,
            chat_id="1",
            talk_id=1,
            type=MessageTypeEnum.TEXT,
            text="Здравствуйте! На какой возраст ищете?",
            file_url=None,
            created_at=datetime.datetime.now(),
        ),
        Message(
            id="3",
            incoming=True,
            chat_id="1",
            talk_id=1,
            type=MessageTypeEnum.TEXT,
            text="На ребенка 13 лет",
            file_url=None,
            created_at=datetime.datetime.now(),
        ),
    ]

    fillable_fields = amo.models.FillableField.objects.filter(chatbot=chatbot)

    available_pipeline_statuses = [
        amo_api.PipelineStatus(
            id=1,
            name="Первичный контакт",
            pipeline_id=1,
            pipeline_name="Воронка",
        ),
        amo_api.PipelineStatus(
            id=2,
            name="Переговоры",
            pipeline_id=1,
            pipeline_name="Воронка",
        ),
        amo_api.PipelineStatus(
            id=3,
            name="Сделка успшно реализована",
            pipeline_id=1,
            pipeline_name="Воронка",
        ),
    ]

    lead = amo_api.Lead(
        id=1,
        pipeline_id=1,
        status_id=1,
        custom_fields_values=None,
    )

    transcriptions = TranscriptionsForMessages({})

    gpt_messages = _get_gpt_messages(chatbot, messages, transcriptions, fillable_fields, available_pipeline_statuses, lead)

    lines = []

    for message in gpt_messages:
        role = message.get("role")
        text = message.get("content")

        lines.append(f"{role}: {text}")

    return "\n\n\n".join(lines)


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
    fields: Iterable[amo.models.FillableField],
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    field_for_new_status: bool,
) -> ResponseTextConfigParam:

    lead_fields = [field for field in fields if field.entity == amo.models.AmoEntity.LEAD.value]
    contact_fields = [field for field in fields if field.entity == amo.models.AmoEntity.CONTACT.value]

    properties = {
        "answer": {"type": "string"},
        "contacts": {
            "type": ["object", "null"],
            "properties": {
                field.name: {
                    "type": ["string", "null"],
                    "description": field.description,
                } for field in contact_fields
            },
            "required": [field.name for field in contact_fields],
            "additionalProperties": False,
        },
        "lead_info": {
            "type": ["object", "null"],
            "properties": {
                field.name: {
                    "type": ["string", "null"],
                    "description": field.description,
                } for field in lead_fields
            },
            "required": [field.name for field in lead_fields],
            "additionalProperties": False,
        },
    }

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

    return text_format


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
