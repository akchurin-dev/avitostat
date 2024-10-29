import asyncio
import openai
from asgiref.sync import sync_to_async
from openai import AsyncOpenAI
from pydantic import BaseModel
import json
from avito_account.models.models import AvitoAccount, Criterion
from base import settings

MODEL = "gpt-4o-2024-08-06"
client = AsyncOpenAI(api_key=settings.OPENAI_SECRET_KEY)


class MessagingSchema(BaseModel):
    answer: str


async def ai_messaging_assist(chat: list, test_from_prod: bool, avito_account: AvitoAccount):
    business_contex = ("""
                       Мы предоставляем услуги по ремонту стиральных машин с выездом на дом
                       Большинство случаев - мы стараемся произвести ремонт на дому у клиента
                       цена варьируется от 2000 до 8000 рублей всё зависит от сложности ремонта
                       а так же заменяемых запчастей.
                       
                       При разговоре старайся не говорить стоимость ремонта при переписке тк в таком
                       случае веорятность потерять клиента - 80 процентов. Очень тактично уходи от ответов 
                       и накидывай клиенту дополнительные вопросы а так же еще более мягко давай понять что 
                       настоящие специалисты никогда не скажут стоимость ремонта без диагностики на месте
                       
                       Стоимость вызда по городу составляет 350 рублей, загородом можешь считать так - 350 + 25 рублей
                        за каждый киломентр(тебе надо будет выяснить сколько километров до населенного пункта.)
                       """)
    chat_text = "\n".join(
        [message.get('direction') + ": " + message.get('content').get("text") for message in
         chat.get('messages') if message.get('type', None) == 'text'])

    prompt = (
        f"Это история переписки: {chat_text}"
        "Ты являешься ассистентом, который отвечает на рутинные вопросы клиента"
        "На вопросы надо отвечать человекоподобно давая исчерпывающую информацию"
        f"Контекст о нашем бизнесе - {business_contex}"
    )

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": prompt},
        ],
        temperature=1.0,
        tools=[openai.pydantic_function_tool(MessagingSchema)]
    )
    raw_result = [x.function.arguments for x in response.choices[0].message.tool_calls]

    # Converting raw_result do usable DICT
    result = {}
    for item in raw_result:
        item_dict = json.loads(item)
        criterion_id = item_dict['criterion_id']
        result[criterion_id] = {
            "meets_criterion": item_dict['meets_criterion'],
            "criterion": item_dict['criterion']
        }

    chat["analyze_by_criteria"] = result
    chat["tokens_by_criteria_analyze"] = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens
    }
    return chat


async def analyze_by_criteria(chats_with_compared_messages: list, test_from_prod: bool,
                              avito_account: AvitoAccount):
    tasks = []

    for chat in chats_with_compared_messages:
        tasks.append(analyze_by_criteria_chat(chat, test_from_prod, avito_account))

    # Выполняем все задачи параллельно
    analyzed_chats = await asyncio.gather(*tasks)

    # Возвращаем список чатов с анализом
    return analyzed_chats
