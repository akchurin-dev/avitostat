from __future__ import annotations

from enum import Enum

from asgiref.sync import  async_to_sync
import httpx
from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from pydantic import BaseModel

from ai_requests import ai_requests
from avito_account.models.models import AvitoAccount
from base import settings
import chat_bot.models
from messaging.api import ChatMessage
from messaging.api import get_chats_last_50_messages
from utils.logging import TraceLogger

MODEL = "gpt-4o-2024-08-06"
client = OpenAI(api_key=settings.OPENAI_SECRET_KEY)


class ChatBotAnswerSchema(BaseModel):
    answer: str
    address: str | None
    mobile: str | None
    whatsapp: str | None
    telegram: str | None
    email: str | None


def contacts_data_prepare(data: ChatBotAnswerSchema) -> dict | None:
    contacts = {key: value for key, value in {
        "address": data.address,
        "mobile": data.mobile,
        "whatsapp": data.whatsapp,
        "telegram": data.telegram,
        "email": data.email,
    }.items() if value is not None}
    if not contacts:
        result = None
    else:
        result = contacts
    return result


def format_chat_history(messages: list[ChatMessage]) -> list[ChatCompletionMessageParam]:
    formatted_messages: list[ChatCompletionMessageParam] = []
    for msg in messages:
        if msg["type"] != 'text':
            continue

        assert msg["content"]["text"] is not None

        if msg["direction"] == "in":
            formatted_messages.append({
                "role": "user",
                "content": msg["content"]["text"],
            })

        if msg["direction"] == "out":
            formatted_messages.append({
                "role": "assistant",
                "content": msg["content"]["text"],
            })

    return formatted_messages


class AIAnswerContacts(BaseModel):
    address: str | None = None
    mobile: str | None = None
    whatsapp: str | None = None
    telegram: str | None = None
    email: str | None = None


class AIAnswerWithContacts(BaseModel):
    answer: str
    nearest_company_branch: str | None = None
    contacts: AIAnswerContacts | None = None
    tokens_completion: int
    tokens_prompt: int


def ai_answer_with_contacts_typed(
    ai_assistant: chat_bot.models.AiChatBot,
    chat: list[ChatMessage],
    ask_location: bool,
) -> AIAnswerWithContacts:

    if not use_gpt_flag():
        return AIAnswerWithContacts.model_validate({
            'answer': "mock answer",
            'contacts': {
                "address": None,
                "mobile": None,
                "whatsapp": None,
                "telegram": None,
                "email": None,
            },
            'tokens_completion': 1,
            'tokens_prompt': 2,
        })

    result = {}

    response = client.beta.chat.completions.parse(
        model=MODEL,
        messages=_get_messages_for_gpt(ai_assistant, chat),
        response_format=_get_schema(ai_assistant.avito_account, ask_location),
        max_tokens=2000,
        timeout=30,
    )
    ai_requests.create_from_chat_completion(response, tlogger=TraceLogger())

    data = response.choices[0].message.parsed
    if data is None:
        raise Exception("GPT response is None")

    result['answer'] = data.answer
    result['nearest_company_branch'] = None

    data_dict = data.model_dump()
    nearest_company_branch_enum: Enum | None = data_dict.get('nearest_company_branch')
    if nearest_company_branch_enum:
        result['nearest_company_branch'] = nearest_company_branch_enum.name

    result['contacts'] = contacts_data_prepare(data)

    result['tokens_completion'] = None
    result['tokens_prompt'] = None

    if response.usage:
        result['tokens_completion'] = response.usage.completion_tokens
        result['tokens_prompt'] = response.usage.prompt_tokens

    return AIAnswerWithContacts.model_validate(result)


def get_example_prompt(aichatbot: chat_bot.models.AiChatBot) -> str:
    example_chat: list[ChatMessage] = [
        {
            "id": "1",
            "author_id": 1,
            "type": "text",
            "direction": "in",
            "content": {"text": "Здравствуйте, хочу купить велосипед"},
        },
        {
            "id": "2",
            "author_id": 2,
            "type": "text",
            "direction": "out",
            "content": {"text": "Здравствуйте! Подскажите для какого возраста ищете?"},
        },
        {
            "id": "3",
            "author_id": 1,
            "type": "text",
            "direction": "in",
            "content": {"text": "На ребенка 13 лет"},
        },
    ]

    messages = _get_messages_for_gpt(
        aichatbot=aichatbot,
        chat=example_chat,
    )

    lines = []

    for message in messages:
        role = message["role"].upper()
        text = message.get("content")

        lines.append(f"{role}: {text}")

    return "\n\n".join(lines)


def _get_messages_for_gpt(aichatbot: chat_bot.models.AiChatBot, chat: list[ChatMessage]) -> list[ChatCompletionMessageParam]:
    chat_history_formatted = format_chat_history(chat)
    print(f"Последнее сообщение для ИИ ответа-{chat_history_formatted[-1]}")

    prompt = "\n\n".join([
        f"Общая информация:\n{aichatbot.total_info}",
        f"Правила при общении:\n{aichatbot.rules}",
        f"Необходимо в ходе разговора наличие шагов:\n{aichatbot.checkpoints}",
        "Ответы давать только на русском языке",
        "Контакты доставать как клиента так и менеджера если имеются в переписке",
    ])

    messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": prompt}, ]

    messages.extend(chat_history_formatted)

    return messages


def _get_schema(avito_account: AvitoAccount, ask_location: bool) -> type[ChatBotAnswerSchema]:
    if not ask_location:
        return ChatBotAnswerSchema

    company_branches = chat_bot.models.CompanyBranch.objects.filter(account=avito_account)

    if len(company_branches) == 0:
        return ChatBotAnswerSchema

    locations = {cb.location_slug: cb.location for cb in company_branches}

    LocationEnum = Enum("LocationEnum", locations)

    class Schema(ChatBotAnswerSchema):
        nearest_company_branch: LocationEnum | None

    return Schema


class ChatSummarySchema(BaseModel):
    paragraph1: str | None
    paragraph2: str | None
    paragraph3: str | None


def chat_summary_data_prepare(data: ChatSummarySchema) -> dict | None:
    parahraphs = {key: value for key, value in {
        "paragraph1": data.paragraph1,
        "paragraph2": data.paragraph2,
        "paragraph3": data.paragraph3,

    }.items() if value is not None}
    if not parahraphs:
        result = None
    else:
        result = parahraphs
    return result


def avito_chat_summary_ai_generator(avito_account: AvitoAccount, chat_id: str, *, tlogger: TraceLogger):
    chat = async_to_sync(get_chats_last_50_messages)(avito_account, chats=[{"id": chat_id}], trace_id=tlogger.trace_id)
    return chat_summary_generator(chat)


class ChatSummaryParagraphs(BaseModel):
    paragraph1: str | None = None
    paragraph2: str | None = None
    paragraph3: str | None = None


class ChatSummary(BaseModel):
    paragraphs: ChatSummaryParagraphs | None = None
    tokens_completion: int
    tokens_prompt: int


def chat_summary_generator_typed(chat) -> ChatSummary:
    summary = chat_summary_generator(chat)
    return ChatSummary.model_validate(summary)


def chat_summary_generator(chat):
    if not use_gpt_flag():
        return {
            'paragraphs': {
                "paragraph1": "paragraph1",
                "paragraph2": "paragraph2",
                "paragraph3": "paragraph3",
            },
            'tokens_completion': 1,
            'tokens_prompt': 2,
        }

    result = {}

    prompt = (f"""Твоя задача - проанализировать переписку чата
        И сгенерировать сводку по чату которая должна содержать пункты:
            1) Суть обращения.
            2) Полный адрес для выезда при наличии(указывать ПОСЛЕДНИЙ УПОМЯНУТЫЙ В ПЕРЕПИСКЕ).
            3) Контакты клиента и назначенное время при наличии.
         - какждый пункт расписать кратко, не более 200 символов каждый.
         
         ВАЖНО - нумеровать пункты пожалуйста ненадо.
         Ответ выдавай НА РУССКОМ ЯЗЫКЕ, проверяй правильность построения предложений на русском при переводе!
        Чат с сообщениями - {chat[-20:]}
        """)

    response = client.beta.chat.completions.parse(
        model=MODEL,
        messages=[
            {"role": "assistant", "content": prompt},
        ],
        response_format=ChatSummarySchema,
        max_tokens=600,
    )
    ai_requests.create_from_chat_completion(response, tlogger=TraceLogger())

    data = response.choices[0].message.parsed
    if data is None:
        return None

    result['paragraphs'] = chat_summary_data_prepare(data)

    result['tokens_completion'] = 0
    result['tokens_prompt'] = 0

    if response.usage:
        result['tokens_completion'] = response.usage.completion_tokens
        result['tokens_prompt'] = response.usage.prompt_tokens

    return result


def use_gpt_flag():
    if settings.ENVIRONMENT != "TESTING":
        return settings.USE_GPT

    url = f"{settings.TEST_DJANGO_HOST}/deep_tests/use-gpt-flag"

    response = httpx.get(url)
    response.raise_for_status()

    return response.text == "True"
