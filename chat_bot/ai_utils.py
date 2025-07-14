from __future__ import annotations

from enum import Enum
from typing import Literal

import httpx
from openai import OpenAI
from openai.types.chat.parsed_chat_completion import ParsedChatCompletion
from openai.types.responses import ResponseInputItemParam
from openai.types.responses import ResponseInputMessageContentListParam
from pydantic import BaseModel

import chat_bot.models
import messaging.api
from ai_requests import ai_requests
from avito_account.models.models import AvitoAccount
from chat_bot.utils import avito_transcriptions
from base import settings
from prompts import prompts
from utils.logging import TraceLogger


MODEL = "gpt-4.1-2025-04-14"
COMPANY_BRANCH_KEy = "nearest_company_branch"

client = OpenAI(api_key=settings.OPENAI_SECRET_KEY)


class ClientContactsSchema(BaseModel):
    address: str | None
    mobile: str | None
    whatsapp: str | None
    telegram: str | None
    email: str | None


class ChatBotAnswerSchema(ClientContactsSchema):
    answer: str


def contacts_data_prepare(data: ClientContactsSchema) -> dict | None:
    contacts = {key: value for key, value in {
        "address": data.address,
        "mobile": data.mobile,
        "whatsapp": data.whatsapp,
        "telegram": data.telegram,
        "email": data.email,
    }.items() if value is not None}

    if len(contacts) == 0:
        return None

    return contacts


def format_chat_history(chat: messaging.api.Chat) -> list[ResponseInputItemParam]:
    formatted_messages: list[ResponseInputItemParam] = []

    for msg in chat.get("messages", []):
        gpt_formatted = avito_message_to_gpt_format(msg)
        if gpt_formatted:
            formatted_messages.append(gpt_formatted)

    return formatted_messages


def avito_message_to_gpt_format(
    message: messaging.api.ChatMessage,
    transcriptions: avito_transcriptions.TranscriptionsForMessages | None = None,
) -> ResponseInputItemParam:

    role: Literal["user", "assistant"] = "user" if message["direction"] == "in" else "assistant"
    content: str | ResponseInputMessageContentListParam | None = None

    if message["type"] == "text":
        content = message["content"].get("text")

    if message["type"] == "image":
        image = message["content"].get("image")
        assert image
        content = [{
            "type": "input_image",
            "image_url": _select_image(image["sizes"]),
            "detail": "low",
        }]

    if message["type"] == "voice" and transcriptions:
        content = transcriptions.get_transcription(message)

    if content is None:
        content = "<message unavailable>"

    return {
        "role": role,
        "content": content,
    }


def _select_image(sizes_to_urls: dict[str, str]) -> str:
    MIN_SIZE = 256 * 256

    widths_heights: list[tuple[int, ...]] = [tuple(map(int, size.split("x"))) for size in sizes_to_urls.keys()]
    pixels = sorted([size[0] * size[1] for size in widths_heights])

    selected_size = pixels[-1]
    pixels = [p for p in pixels if p >= MIN_SIZE]
    if pixels:
        selected_size = pixels[0]

    width, height = [(w, h) for w, h in widths_heights if w * h == selected_size][0]

    return sizes_to_urls[f"{width}x{height}"]


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


def generate_answer_and_parse_contacts(
    ai_assistant: chat_bot.models.AiChatBot,
    chat: messaging.api.Chat,
    ask_location: bool,
    *,
    tlogger: TraceLogger,
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

    assert ai_assistant.account

    response = client.beta.chat.completions.parse(
        model=MODEL,
        messages=_get_messages_for_gpt(ai_assistant, chat, extract_contacts_only=False, tlogger=tlogger),
        response_format=_get_schema(ai_assistant.account, ask_location, ChatBotAnswerSchema),
        max_tokens=2000,
        timeout=30,
    )
    ai_requests.create_from_chat_completion(response, tlogger=tlogger)

    return parse_response(response)


def parse_contacts(
    chatbot: chat_bot.models.AiChatBot,
    chat: messaging.api.Chat,
    ask_location: bool,
    *,
    tlogger: TraceLogger,
) -> AIAnswerWithContacts:

    if not use_gpt_flag():
        return AIAnswerWithContacts.model_validate({})

    response = client.beta.chat.completions.parse(
        model=MODEL,
        messages=_get_messages_for_gpt(chatbot, chat, extract_contacts_only=True, tlogger=tlogger),
        response_format=_get_schema(chatbot.account, ask_location, ClientContactsSchema),
    )
    ai_requests.create_from_chat_completion(response, tlogger=tlogger)

    return parse_response(response)


def parse_response(response: ParsedChatCompletion) -> AIAnswerWithContacts:
    data = response.choices[0].message.parsed

    if data is None:
        raise_gpt_response_is_none()

    assert data is not None

    result = {
        "answer": "",
        COMPANY_BRANCH_KEy: None,
        "contacts": contacts_data_prepare(data),
    }

    data_dict = data.model_dump()

    result["answer"] = data_dict.get("answer", "")

    nearest_compant_branch_enum: Enum | None = data_dict.get(COMPANY_BRANCH_KEy)
    if nearest_compant_branch_enum:
        result[COMPANY_BRANCH_KEy] = nearest_compant_branch_enum.name

    result["tokens_completion"] = 0
    result["tokens_prompt"] = 0

    if response.usage:
        result["tokens_completion"] = response.usage.completion_tokens
        result["tokens_prompt"] = response.usage.prompt_tokens

    return AIAnswerWithContacts.model_validate(result)


def _get_messages_for_gpt(
    aichatbot: chat_bot.models.AiChatBot,
    chat: messaging.api.Chat,
    extract_contacts_only: bool,
    *,
    tlogger: TraceLogger,
) -> list[ResponseInputItemParam]:

    prompt = _get_system_message(aichatbot, chat, extract_contacts_only, tlogger=tlogger)

    messages: list[ResponseInputItemParam] = [{"role": "system", "content": prompt}]

    chat_history_formatted = format_chat_history(chat)
    tlogger.info(f"Последнее сообщение для ИИ ответа-{chat_history_formatted[-1]}")
    messages.extend(chat_history_formatted)

    return messages


def _get_system_message(
    chatbot: chat_bot.models.AiChatBot,
    chat: messaging.api.Chat,
    extract_contacts_only: bool,
    *,
    tlogger: TraceLogger,
) -> str:

    lines: list[str] = [
        "Контакты доставать как клиента так и менеджера если имеются в переписке",
    ]

    if extract_contacts_only:
        return lines[0]

    chat_str = _chat_to_str(chat)
    prompts_qs = chat_bot.models.AvitoPrompt.objects.filter(chatbot=chatbot)
    prompt_base = prompts.define_prompt(prompts_qs, chat_str, tlogger=tlogger)

    if prompt_base:
        lines.append(prompt_base)

    lines.append("Ответы давать только на русском языке")

    return "\n\n".join(lines)


def _chat_to_str(chat: messaging.api.Chat) -> str:
    replicas: list[str] = []

    for message in chat.get("messages", []):
        role = "Manager"
        if message["direction"] == "in":
            role = "Client"

        text = message["content"].get("text")
        if text is None:
            text = "Not text format"

        replicas.append(role + ": " + text)

    return "\n".join(replicas)


def _get_schema(avito_account: AvitoAccount, ask_location: bool, base_schema) -> type:
    if not ask_location:
        return base_schema

    company_branches = chat_bot.models.CompanyBranch.objects.filter(account=avito_account)

    if len(company_branches) == 0:
        return base_schema

    locations = {cb.location_slug: cb.location for cb in company_branches}

    LocationEnum = Enum("LocationEnum", locations)

    class Schema(base_schema):
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
    chat = messaging.api.MessagingAPISync.get_chat_last_50_messages_by_chat_id(
        avito_account=avito_account,
        chat_id=chat_id,
        trace_id=tlogger.trace_id,
    )

    messages = chat.get("messages")
    assert messages

    return generate_chat_summary(messages)


class ChatSummaryParagraphs(BaseModel):
    paragraph1: str | None = None
    paragraph2: str | None = None
    paragraph3: str | None = None


class ChatSummary(BaseModel):
    paragraphs: ChatSummaryParagraphs | None = None
    tokens_completion: int
    tokens_prompt: int


def generate_chat_summary(chat: list) -> ChatSummary:
    if not use_gpt_flag():
        return ChatSummary.model_validate({
            'paragraphs': {
                "paragraph1": "paragraph1",
                "paragraph2": "paragraph2",
                "paragraph3": "paragraph3",
            },
            'tokens_completion': 1,
            'tokens_prompt': 2,
        })

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
        raise_gpt_response_is_none()

    assert data is not None

    result['paragraphs'] = chat_summary_data_prepare(data)

    result['tokens_completion'] = 0
    result['tokens_prompt'] = 0

    if response.usage:
        result['tokens_completion'] = response.usage.completion_tokens
        result['tokens_prompt'] = response.usage.prompt_tokens

    return ChatSummary.model_validate(result)


def use_gpt_flag():
    if settings.ENVIRONMENT != "TESTING":
        return settings.USE_GPT

    url = settings.DJANGO_BASE_URL + "/deep_tests/use-gpt-flag"

    response = httpx.get(url)
    response.raise_for_status()

    return response.text == "True"


def raise_gpt_response_is_none():
    raise Exception("GPT response is None")
