from openai import OpenAI
from pydantic import BaseModel, EmailStr

from avito_account.models.models import AvitoAccount
from base import settings
from chat_bot.models import AiChatBot
from messaging.api import get_chats_messages

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


def ai_answer_assist(ai_assistant: AiChatBot, chat: list, ):
    result = {}
    prompt = (
        f"Общая информация:{ai_assistant.total_info}"
        f"Правила при общении:{ai_assistant.rules}"
        f"Необходимо в ходе разговора наличие шагов:{ai_assistant.checkpoints}"
        f"История переписки:{chat}"
        "Ответы давать только на русском языке"
    )
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "assistant", "content": prompt},
        ],
        response_format=ChatBotAnswerSchema,
        max_tokens=300,
    )
    data = response.choices[0].message.parsed
    if data is not None:
        result['answer'] = data.answer
        result['contacts'] = contacts_data_prepare(data)
        result['tokens_completion'] = response.usage.completion_tokens
        result['tokens_prompt'] = response.usage.prompt_tokens
        return result


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


async def chat_summary_generator(avito_account: AvitoAccount, chat_id: str):
    result = {}
    chat_with_messages = await get_chats_messages(avito_account, chats=[{"id": chat_id}])

    prompt = (f"""Твоя задача - проанализировать переписку чата
        И сгенерировать сводку по чату которая должна содержать пункты:
            1) Суть поломки стиралки если выявлено.
            2) Адрес для выезда.
            3) Контакты клиента и время при наличии.
         - какждый пункт расписать кратко, не более 200 символов каждый.
         Ответ выдавай НА РУССКОМ ЯЗЫКЕ, проверяй правильность построения предложений на русском при переводе!
        Чат с сообщениями - {chat_with_messages}
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
