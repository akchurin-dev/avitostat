from pydantic import BaseModel

import amo.models
from amo.utils.amo_messages import Message
from chat_bot.ai_utils import client
from chat_bot.ai_utils import MODEL
from chat_bot.ai_utils import use_gpt_flag


class AIAnswerPayload(BaseModel):
    answer: str
    contacts: dict[str, str] | None = None
    lead_info: dict[str, str] | None = None


class AIAnswer(BaseModel):
    payload: AIAnswerPayload
    tokens_completion: int = 0
    tokens_prompt: int = 0


def generate_answer(chatbot: amo.models.AmoChatBot, messages: list[Message]) -> AIAnswer:
    if not use_gpt_flag():
        return AIAnswer(payload=AIAnswerPayload(answer="mock answer"))

    fillable_fields = list(amo.models.FillableField.objects.filter(chatbot=chatbot))
    prompt = _get_prompt(chatbot, fillable_fields)
    dialog_str = _dialog_to_str(messages)
    schema = _get_answer_schema(fillable_fields)

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
        tokens_completion=0, # TODO calculate tokens
        tokens_prompt=0, # TODO calculate tokens
    )


def _get_answer_schema(fields: list[amo.models.FillableField]) -> dict:
    lead_fields = [field for field in fields if field.entity == amo.models.AmoEntity.LEAD.value]
    contact_fields = [field for field in fields if field.entity == amo.models.AmoEntity.CONTACT.value]

    schema = {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "contacts": {
                "type": "object",
                "properties": {field.name: {"type": "string"} for field in contact_fields},
                "required": [field.name for field in contact_fields],
                "additionalProperties": False,
            },
            "lead_info": {
                "type": "object",
                "properties": {field.name: {"type": "string"} for field in lead_fields},
                "required": [field.name for field in lead_fields],
                "additionalProperties": False,
            },
        },
        "required": ["answer", "contacts", "lead_info"],
        "additionalProperties": False,
    }

    return schema


def _dialog_to_str(dialog: list[Message]) -> str:
    lines = ["Чат с клиентом:"]

    for message in dialog:
        author = "Клиент" if message.incoming else "Менеджер"
        lines.append(f"{author}: {message.text}")

    return "\n".join(lines)


def _get_prompt(chatbot: amo.models.AmoChatBot, fields: list[amo.models.FillableField]) -> str:
    prompt = (
        "Прочитай переписку, достань из нее данные о сделке, контакты и сгенерируй ответ клиенту"
        "Ответы давать только на русском языке"
        "Контакты доставать как клиента так и менеджера если имеются в переписке"
    )

    prompt = _add_chatbot_prompt(prompt, chatbot)
    prompt = _add_fillable_fields_prompt(prompt, fields)

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


def _add_fillable_fields_prompt(prompt: str, fields: list[amo.models.FillableField]) -> str:
    new_articles = ["Тебе нужно постараться узнать данные для следующих полей:"]

    for field in fields:
        new_articles.append((
            f"Поле: {field.name}.\n"
            f"Описание: {field.description}."
        ))

    new_text = "\n\n\n".join(new_articles)

    if prompt:
        prompt += "\n\n"

    return prompt + new_text
