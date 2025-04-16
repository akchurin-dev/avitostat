from pydantic import BaseModel

import amo.models
from amo.utils import amo_api
from amo.utils.amo_messages import Message
from chat_bot.ai_utils import client
from chat_bot.ai_utils import MODEL
from chat_bot.ai_utils import use_gpt_flag
from utils.logging import TraceLogger


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
    account: amo.models.AmoAccount,
    lead_id: int | str,
    *,
    tlogger: TraceLogger,
) -> AIAnswer:

    if not use_gpt_flag():
        return AIAnswer(payload=AIAnswerPayload(answer="mock answer"))

    fillable_fields = list(amo.models.FillableField.objects.filter(chatbot=chatbot))
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

    current_status = None

    for status in available_pipeline_statuses:
        if status.id == lead.status_id:
            current_status = status

    if current_status is None:
        raise Exception(f"Status (id={lead.status_id}) not found in pipeline (id={lead.pipeline_id})")

    prompt = _get_prompt(chatbot, fillable_fields, available_pipeline_statuses, current_status)
    dialog_str = _dialog_to_str(messages)
    schema = _get_answer_schema(
        fields=fillable_fields,
        available_pipeline_statuses=available_pipeline_statuses,
        field_for_new_status=not chatbot.change_status_only_when_qualification,
    )

    response = client.responses.create(
        model=MODEL,
        input=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": dialog_str},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "chat_answer",
                "schema": schema,
                "strict": True,
            },
        },
        max_output_tokens=2000,
    )

    return AIAnswer(
        payload=AIAnswerPayload.model_validate_json(response.output_text),
        tokens_completion=0,  # TODO calculate tokens
        tokens_prompt=0,  # TODO calculate tokens
    )


def _get_answer_schema(
    fields: list[amo.models.FillableField],
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    field_for_new_status: bool,
) -> dict:

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

    return schema


def _dialog_to_str(dialog: list[Message]) -> str:
    lines = ["Чат с клиентом:"]

    for message in dialog:
        author = "Клиент" if message.incoming else "Менеджер"
        lines.append(f"{author}: {message.text}")

    return "\n".join(lines)


def _get_prompt(
    chatbot: amo.models.AmoChatBot,
    fields: list[amo.models.FillableField],
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

    new_text = "\n\n".join([title + "\n" + titles_and_descriptions[title] for title in titles_ordered])

    if prompt:
        prompt += "\n\n"

    return prompt + new_text


def _add_pipelines_prompt(
    prompt: str,
    pipeline_status_update_rules: str,
    available_pipeline_statuses: list[amo_api.PipelineStatus],
    current_status: amo_api.PipelineStatus,
) -> str:

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


def _add_fields_prompt(prompt: str, fields: list[amo.models.FillableField]) -> str:
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
