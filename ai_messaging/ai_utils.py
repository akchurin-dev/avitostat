from openai import AsyncOpenAI
from ai_messaging.models import AiAssistant
from base import settings

MODEL = "gpt-4o-2024-08-06"
client = AsyncOpenAI(api_key=settings.OPENAI_SECRET_KEY)


async def ai_answer_assist(ai_assistant: AiAssistant, chat: list):
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
    print(response)
    if response is not None:
        message = response.choices[0].message.content
        return message
