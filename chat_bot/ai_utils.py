from __future__ import annotations

import json
from enum import Enum
from typing import Any
from typing import Literal

import httpx
from openai.types.responses import ResponseInputItemParam
from pydantic import BaseModel

import chat_bot.models
import messaging.api
from ai_requests import ai_requests
from avito_account.models.models import AvitoAccount
from chat_bot.utils import messages_formating
from base import settings
from prompts import prompts
from utils import ai_helper
from utils.logging import TraceLogger
from utils.openai_helper import MODEL
from utils.openai_helper import client


COMPANY_BRANCH_KEy = "nearest_company_branch"


class ClientContactsSchema(BaseModel):
    address: str | None
    mobile: str | None
    whatsapp: str | None
    telegram: str | None
    email: str | None


class ChatBotAnswerSchema(ClientContactsSchema):
    answer: str


def contacts_data_prepare(data: dict) -> dict | None:
    contacts = {key: value for key, value in {
        "address": data.get("address"),
        "mobile": data.get("mobile"),
        "whatsapp": data.get("whatsapp"),
        "telegram": data.get("telegram"),
        "email": data.get("email"),
    }.items() if value is not None}

    if len(contacts) == 0:
        return None

    return contacts


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

    response, _ = ai_helper.parse_completion(
        openai_input=_get_openai_input(ai_assistant, chat, extract_contacts_only=False, tlogger=tlogger),
        model=_get_schema(ai_assistant.account, ask_location, ChatBotAnswerSchema),
        tag=f"Avito | {ai_assistant.account.name} | generate answer and parse contacts",
        tlogger=tlogger,
    )

    return parse_response(response.answer_text, response.input_tokens, response.output_tokens)


def parse_contacts(
    chatbot: chat_bot.models.AiChatBot,
    chat: messaging.api.Chat,
    ask_location: bool,
    *,
    tlogger: TraceLogger,
) -> AIAnswerWithContacts:

    if not use_gpt_flag():
        return AIAnswerWithContacts.model_validate({})

    response, _ = ai_helper.parse_completion(
        openai_input=_get_openai_input(chatbot, chat, extract_contacts_only=True, tlogger=tlogger),
        model=_get_schema(chatbot.account, ask_location, ClientContactsSchema),
        tag=f"Avito | {chatbot.account.name} | parse contacts",
        tlogger=tlogger,
    )

    return parse_response(
        json_str=response.answer_text,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
    )


def parse_response(json_str: str, input_tokens: int, output_tokens: int) -> AIAnswerWithContacts:
    data: dict = json.loads(json_str)

    if data is None:
        raise_gpt_response_is_none()

    assert data is not None

    result: dict[str, Any] = {
        "answer": "",
        COMPANY_BRANCH_KEy: None,
        "contacts": contacts_data_prepare(data),
    }

    result["answer"] = data.get("answer", "")

    nearest_compant_branch_enum: str = data.get(COMPANY_BRANCH_KEy, "")
    if nearest_compant_branch_enum != "":
        result[COMPANY_BRANCH_KEy] = nearest_compant_branch_enum

    result["tokens_completion"] = output_tokens
    result["tokens_prompt"] = input_tokens

    return AIAnswerWithContacts.model_validate(result)


def _get_openai_input(
    aichatbot: chat_bot.models.AiChatBot,
    chat: messaging.api.Chat,
    extract_contacts_only: bool,
    *,
    tlogger: TraceLogger,
) -> list[ResponseInputItemParam]:

    chat_gpt_format = messages_formating.avito_chat_to_gpt_format(chat.get("messages", []), transcriptions=None)

    prompt = _get_system_message(aichatbot, chat_gpt_format, extract_contacts_only, tlogger=tlogger)

    messages: list[ResponseInputItemParam] = [{"role": "system", "content": prompt}]

    tlogger.info(f"Последнее сообщение для ИИ ответа-{chat_gpt_format[-1]}")
    messages.extend(chat_gpt_format)

    return messages


def _get_system_message(
    chatbot: chat_bot.models.AiChatBot,
    messages: list[ResponseInputItemParam],
    extract_contacts_only: bool,
    *,
    tlogger: TraceLogger,
) -> str:

    lines: list[str] = [
        "Контакты доставать как клиента так и менеджера если имеются в переписке",
    ]

    if extract_contacts_only:
        return lines[0]

    chat_str = messages_formating.gpt_format_to_str(messages)
    prompts_qs = chat_bot.models.AvitoPrompt.objects.filter(chatbot=chatbot)
    prompt_base = prompts.define_prompt(
        prompts_qs,
        chat_str,
        module="Avito",
        account_name=chatbot.account.name or "",
        tlogger=tlogger,
    )

    if prompt_base:
        lines.append(prompt_base)

    lines.append("Ответы давать только на русском языке")

    return "\n\n".join(lines)


def _get_schema(avito_account: AvitoAccount, ask_location: bool, base_schema) -> type:
    if not ask_location:
        return base_schema

    company_branches = chat_bot.models.CompanyBranch.objects.filter(account=avito_account)

    if len(company_branches) == 0:
        return base_schema

    locations = {cb.location_slug: cb.location for cb in company_branches}

    LocationEnum = Enum("LocationEnum", locations)  # type: ignore

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
    chat = messaging.api.get_chat_last_50_messages_by_chat_id(
        avito_account=avito_account,
        chat_id=chat_id,
        tlogger=tlogger,
    )

    messages = chat.get("messages")
    assert messages

    return generate_chat_summary("Avito", avito_account.name or "", messages)


class ChatSummaryParagraphs(BaseModel):
    paragraph1: str | None = None
    paragraph2: str | None = None
    paragraph3: str | None = None


class ChatSummary(BaseModel):
    paragraphs: ChatSummaryParagraphs | None = None
    tokens_completion: int
    tokens_prompt: int


def generate_chat_summary(module: Literal["Avito", "Amo"], account_name: str, chat: list) -> ChatSummary:
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

    result: dict[str, Any] = {}

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
    ai_requests.create_from_openai_completion(
        tag=f"{module} | {account_name} | generate chat summary",
        completion=response,
        tlogger=TraceLogger(),
    )

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
