import time

import openai
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from openai import OpenAI
import os

from pydantic import BaseModel

from avito_account.models import AvitoAccount, Criterion

load_dotenv()
ENVIRONMENT = os.getenv('ENVIRONMENT')

MODEL = "gpt-4o-2024-08-06"
client = OpenAI(api_key=os.environ.get("OPENAI_SECRET_KEY"))


# TODO I tried change to ASYNC methods for analyze , but not see different in speed
async def messaging_total_analyze(chats_with_compared_messages: list, test_from_prod: bool,
                                  avito_account: AvitoAccount):
    # Checking count of messages fo analytics
    if ENVIRONMENT == 'DEVELOPMENT' or test_from_prod:
        chats_with_compared_messages = chats_with_compared_messages[:5]  #  For testing 5 items  for economy
    else:
        chats_with_compared_messages = chats_with_compared_messages[:15]

    for chat in chats_with_compared_messages:
        chat_text = "\n".join(
            [message.get('direction') + ": " + message.get('content').get("text") for message in chat.get('messages') if
             message.get('type', None) == 'text'])
        prompt = f"""
                    Ты - эксперт по клиентскому обслуживанию.
                    Твоя задача - проанализировать переписку между менеджером (assistant) и клиентом (user).
                    Оцени чат целиком с точки зрения качества обслуживания клиента в два этапа,
                    Первый этап:

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

        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
            ],
            temperature=1.0
        )
        chat["analyze"] = completion.choices[0].message.content
    return chats_with_compared_messages


class CriterionAnalyzeSchema(BaseModel):
    criterion_id: int
    meets_criterion: bool
    criterion: str


async def analyze_by_criteria(chats_with_compared_messages: list, avito_account: AvitoAccount):
    if avito_account.analytic_schema_id:
        criteria = await sync_to_async(list)(Criterion.objects.filter(schema_id=avito_account.analytic_schema_id))
        criteria_dict = {criterion.id: criterion.name for criterion in criteria}

        for chat in chats_with_compared_messages:
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
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                ],
                temperature=1.0,
                tools=[openai.pydantic_function_tool(CriterionAnalyzeSchema)]
            )
            chat["analyze_by_criteria"] = [x.function.arguments for x in response.choices[0].message.tool_calls]

    return chats_with_compared_messages
