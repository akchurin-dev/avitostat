from pprint import pprint

from asgiref.sync import sync_to_async, async_to_sync
from openai import OpenAI
from pydantic import BaseModel, EmailStr

from avito_account.models.models import AvitoAccount
from base import settings
from base.settings import ENVIRONMENT
from chat_bot.models import AiChatBot
from messaging.api import get_chats_last_50_messages

MODEL = "gpt-4o-2024-08-06"
client = OpenAI(api_key=settings.OPENAI_SECRET_KEY)


class ChatBotAnswerSchema(BaseModel):
    answer: str
    address: str | None
    mobile: str | None
    whatsapp: str | None
    telegram: str | None
    email: str | None


def contacts_data_prepare(data: dict) -> dict | None:
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


def format_chat_history(messages):
    formatted_messages = []
    for msg in messages:
        if msg.get('type') != 'text':
            continue
        message_text = msg['content']['text']
        if msg['direction'] == 'in':
            formatted_messages.append({"role": "user", "content": message_text})
        elif msg['direction'] == 'out':
            formatted_messages.append({"role": "assistant", "content": message_text})
    return formatted_messages


def ai_answer_assist(ai_assistant: AiChatBot, chat: list, ):
    try:
        result = {}
        chat_history_formatted = format_chat_history(chat)
        print(f"Последнее сообщение для ИИ ответа-{chat_history_formatted[-1]}")
        prompt = (
            f"Общая информация:{ai_assistant.total_info}"
            f"Правила при общении:{ai_assistant.rules}"
            f"Необходимо в ходе разговора наличие шагов:{ai_assistant.checkpoints}"
            "Ответы давать только на русском языке"
        )
        messages = [{"role": "system", "content": prompt}, ]
        messages.extend(chat_history_formatted)
        response = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=messages,
            response_format=ChatBotAnswerSchema,
            max_tokens=2000,
        )
        data = response.choices[0].message.parsed
        if data is not None:
            result['answer'] = data.answer
            result['contacts'] = contacts_data_prepare(data)
            result['tokens_completion'] = response.usage.completion_tokens
            result['tokens_prompt'] = response.usage.prompt_tokens
            return result
    except Exception:
        raise Exception


class ChatSummarySchema(BaseModel):
    paragraph1: str | None
    paragraph2: str | None
    paragraph3: str | None


def chat_summary_data_prepare(data: dict) -> dict | None:
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


def chat_summary_generator(avito_account: AvitoAccount, chat_id: str):
    result = {}
    chat_with_messages = async_to_sync(get_chats_last_50_messages)(avito_account, chats=[{"id": chat_id}])

    prompt = (f"""Твоя задача - проанализировать переписку чата
        И сгенерировать сводку по чату которая должна содержать пункты:
            1) Суть обращения.
            2) Адрес для выезда при наличии(указывать ПОСЛЕДНИЙ УПОМЯНУТЫЙ В ПЕРЕПИСКЕ).
            3) Контакты клиента и назначенное время при наличии.
         - какждый пункт расписать кратко, не более 200 символов каждый.
         Ответ выдавай НА РУССКОМ ЯЗЫКЕ, проверяй правильность построения предложений на русском при переводе!
        Чат с сообщениями - {chat_with_messages[-20:]}
        """)

    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "assistant", "content": prompt},
        ],
        response_format=ChatSummarySchema,
        max_tokens=600,
    )
    data = response.choices[0].message.parsed
    if data is not None:
        result['paragraphs'] = chat_summary_data_prepare(data)
        result['tokens_completion'] = response.usage.completion_tokens
        result['tokens_prompt'] = response.usage.prompt_tokens
        return result
