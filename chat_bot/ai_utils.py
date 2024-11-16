from openai import OpenAI
from pydantic import BaseModel, EmailStr

from base import settings
from chat_bot.models import AiChatBot

MODEL = "gpt-4o-2024-08-06"
client = OpenAI(api_key=settings.OPENAI_SECRET_KEY)


class ChatBotAnswerSchema(BaseModel):
    answer: str
    address: str | None
    mobile_number: str | None
    whatsapp_number: str | None
    telegram_number: str | None
    email: str | None


def contacts_data_prepare(data: dict) -> dict | None:
    contacts = {key: value for key, value in {
        "address": data.address,
        "mobile_number": data.mobile_number,
        "whatsapp_number": data.whatsapp_number,
        "telegram_number": data.telegram_number,
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
        return result, response.usage.completion_tokens, response.usage.prompt_tokens
