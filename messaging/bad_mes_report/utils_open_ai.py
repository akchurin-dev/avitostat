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


async def analyze_chat(chat):
    chat_text = "\n".join(
        [message.get('direction') + ": " + message.get('content').get("text") for message in chat.get('messages') if
         message.get('type', None) == 'text'])
    prompt = f"""
                Ты - эксперт по клиентскому обслуживанию.
                Твоя задача - проанализировать переписку между менеджером (assistant) и клиентом (user).
                Оцени чат целиком с точки зрения качества обслуживания клиента.

                        Формат переписки:
                        - Сначала идет описание роли собеседника, затем его текст
                        - in - это клиент
                        - out - это менеджер

                                    Продажа состоит из следующих этапов:
                        1.Установление контакта 
                        2.Выявление потребности
                        3.Коммерческое предложение
                        4.Оплата 
             

                        Обрати внимание на следующие аспекты:
                        1. Установление контакта
                            -Приветствие
                            -Представить себя и компанию
                            
                        2. Готовность помочь клиенту найти интересующую информацию
                            - Выяснить потребность  
                           - Выяснил ли менеджер, где клиенту удобнее получить полную информацию:
                           - WhatsApp
                           - почта
                           - по номеру телефона
                           - через Авито

                        3. Сделать КП 
                            Предложить вилку цен
                            
                        4. Закрыть человека на сделку
                            Оплату

                        6. Завершение диалога менеджером:
                           - Менеджер должен всегда заканчивать диалог, он ведущий
                           - Должно быть понятно, чем закончился разговор:
                             * Клиент берет товар/услугу
                             * Клиент думает
                             * Клиенту не нравится или не покупает
                        
                        Если пункты 1,2,3 не выполняются, то бей тревогу и начинай бить менеджера)
                        
                        Выяви факты, которые могли бы препятствовать продаже услуги/товара, например:
                        - нету приветствия
                        - не выяснил потребность клиента
                        - не предлагает пути решения запроса
                        - не закрывает на сделку
                        
                        Важно: НЕ учитывай следующие аспекты:
                        1. То, что менеджер просит контактный номер
                        2. Игнорирование системных сообщений о запрете перехода в другие мессенджеры
                        
                        Формат ответа:
                        1. Краткое общее впечатление (1-2 предложения)
                        2. 2-3 ключевых замечания о работе менеджера (короткие и лаконичные)
                        3. Одно предложение о том, что было сделано хорошо
                        4. Текст переписки не надо включать в ответ.
                        
                        Помни: цель - выявить основные моменты, которые могут повлиять на успешность продажи, без излишней придирчивости. Сосредоточься на наиболее важных аспектах общения.
                        
                        Переписка:
                        {chat_text}
                        """

    completion = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": prompt},
        ],
        temperature=1.0
    )
    chat["analyze"] = completion.choices[0].message.content
    chat["tokens_total_analyze"] = {
        "prompt_tokens": completion.usage.prompt_tokens,
        "completion_tokens": completion.usage.completion_tokens
    }
    return chat


async def messaging_total_analyze(ready_chats: list, period: str = "week"):
    if period == "week":
        ready_chats = ready_chats[:15]
    elif period == "month":
        ready_chats = ready_chats[:30]

    tasks = []

    for chat in ready_chats:
        tasks.append(analyze_chat(chat))

    # Выполняем все задачи параллельно
    analyzed_chats = await asyncio.gather(*tasks)

    # Возвращаем список чатов с анализом
    return analyzed_chats


class CriterionAnalyzeSchema(BaseModel):
    criterion_id: int
    meets_criterion: bool
    criterion: str


async def analyze_by_criteria_chat(chat: list, test_from_prod: bool, avito_account: AvitoAccount):
    if avito_account.analytic_schema_id:
        criteria = await sync_to_async(list)(Criterion.objects.filter(schema_id=avito_account.analytic_schema_id))
    else:
        criteria = await sync_to_async(list)(Criterion.objects.filter(schema_id=1))
    if not criteria:  # Проверяем, есть ли критерии
        criteria = await sync_to_async(list)(Criterion.objects.filter(schema_id=1))

    criteria_dict = {criterion.id: criterion.name for criterion in criteria}
    chat_text = "\n".join(
        [message.get('direction') + ": " + message.get('content').get("text") for message in
         chat.get('messages') if
         message.get('type', None) == 'text'])

    prompt = (
            f"Here is a conversation between a call center operator and a client: {chat_text}"
            "Format of the conversation:"
            "- First, the role of the speaker is described, followed by their text"
            "- 'in' indicates the client"
            "- 'out' indicates the manager"
            + (
                f"and a dictionary of criteria with criterion identifiers as keys and criteria as "
                f"values, {criteria_dict}" if criteria else ""
            )
            + "perform the following steps: "
            + ("\n - Evaluate each criterion." if criteria else "")
    )
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": prompt},
        ],
        temperature=1.0,
        tools=[openai.pydantic_function_tool(CriterionAnalyzeSchema)]
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
