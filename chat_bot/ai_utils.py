import json
from pprint import pprint

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel

from base import settings
from chat_bot.models import AiChatBot

MODEL = "gpt-4o-2024-08-06"
client = AsyncOpenAI(api_key=settings.OPENAI_SECRET_KEY)


class ChatBotAnswerSchema(BaseModel):
    answer: str
    target_action_success: bool


async def ai_answer_assist(ai_assistant: AiChatBot, chat: list,):
    result = {}
    prompt = (
        f"Общая информация:{ai_assistant.total_info}"
        f"Правила при общении:{ai_assistant.rules}"
        f"Необходимо в ходе разговора наличие шагов:{ai_assistant.checkpoints}"
        f"История переписки:{chat}",
        f"Достигнуто ли в ходе переписки целевое дейтствие? - {ai_assistant.target_action}"
    )
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "assistant", "content": prompt},
        ],
        temperature=1,
        max_tokens=300,
        tools=[openai.pydantic_function_tool(ChatBotAnswerSchema)]
    )
    if response is not None:
        item_dict = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        result['answer'] = item_dict['answer']
        result['target_action_success'] = item_dict['target_action_success']

        # message = response.choices[0].message.content
        tokens_completion = response.usage.completion_tokens
        tokens_prompt = response.usage.prompt_tokens
        return result, tokens_completion, tokens_prompt
