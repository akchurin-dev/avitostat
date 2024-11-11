from pprint import pprint

from openai import AsyncOpenAI
from base import settings
from chat_bot.models import AiChatBot

MODEL = "gpt-4o-2024-08-06"
client = AsyncOpenAI(api_key=settings.OPENAI_SECRET_KEY)


async def ai_answer_assist(ai_assistant: AiChatBot, chat: list):
    prompt = (
        f"Общая информация:{ai_assistant.total_info}"
        f"Правила при общении:{ai_assistant.rules}"
        f"Необходимо в ходе разговора наличие шагов:{ai_assistant.checkpoints}"
        f"История переписки:{chat}"
    )
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "assistant", "content": prompt},
        ],
        temperature=1,
        max_tokens=300,
    )
    if response is not None:
        message = response.choices[0].message.content
        tokens_completion = response.usage.completion_tokens
        tokens_prompt = response.usage.prompt_tokens
        return message, tokens_completion, tokens_prompt
