from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from openai import OpenAI
import os

from avito_account.models import AvitoAccount, Criterion

load_dotenv()
ENVIRONMENT = os.getenv('ENVIRONMENT')

MODEL = "gpt-4o"
client = OpenAI(api_key=os.environ.get("OPENAI_SECRET_KEY"))


# TODO I tried change to ASYNC methods for analyze , but not see different in speed
def messaging_total_analyze(chats_with_compared_messages: list, test_from_prod: bool):
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

        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
            ],
            temperature=1.0
        )
        chat["analyze"] = completion.choices[0].message.content
    return chats_with_compared_messages


async def analyze_by_criteria(chats_with_compared_messages: list, avito_account: AvitoAccount):
    criteria = None
    if avito_account.analytic_schema_id:
        criteria = await sync_to_async(list)(Criterion.objects.filter(schema_id=avito_account.analytic_schema_id))
        criteria_dict = {criterion.id: criterion.name for criterion in criteria}
        analyze_all_chats = []

        for chat in chats_with_compared_messages:
            prompt = (
                    "Дан разговор между оператором колл-центра и клиентом, "
                    + (
                        "и словарь критериев с идентификаторами критериев в качестве ключей и критериями в качестве значений, "
                        if criteria
                        else ""
                    )
                    + "выполните следующие шаги: "
                      "\n - Разделите разговор по ролям, создавая отдельные записи для каждого фрагмента диалога в массиве JSON."
                    + ("\n - Дайте оценку для каждого критерия." if criteria else "")
                    + "\n Предоставьте результат в следующем формате JSON:"
                      '\n {"conversation": [{"agent": "text of agent here"}, {"customer": "text of customer here"}, ...], '
                    + (
                        '"criteria": {"criterion_id_1": {"meets_criterion": true/false, "evaluation": "your evaluation here"},'
                        ' "criterion_id_2": {"meets_criterion": true/false, "evaluation": "your evaluation here"}, ...} '
                        if criteria
                        else ""
                    )
                    + "}"
            )

            user_content = (
                    f"Conversation:\n{chat['messages']}"
                    + ("\nCriteria:\n" + str(criteria_dict) if criteria else "")
            )

            response = client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                temperature=0,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            analyze_all_chats.append(response.choices[0].message.content)

    return analyze_all_chats
