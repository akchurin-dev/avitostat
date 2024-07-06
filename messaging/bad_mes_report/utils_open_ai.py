from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
MODEL = "gpt-4o"
client = OpenAI(api_key=os.environ.get("OPENAI_SECRET_KEY"))


def compare_messages_for_ai(chats_with_raw_messages: list):
    compared_messages = []
    for chat in chats_with_raw_messages:
        chat_id = chat.get('id')
        if any(message['type'] == 'text' for message in chat.get("messages")):  # do we have any text type message?
            compared_messages.append({'chat_id': chat_id, 'messages': []})
            for message in chat.get('messages')[-30:]:  # TODO only last 10 messages
                if message['direction'] == 'in' and message.get('type', None) == 'text':  # becouse we have appCall
                    compared_messages[-1].get('messages').append(
                        {"role": "user", "content": message['content']['text']})
                elif message['direction'] == 'out' and message.get('type', None) == 'text':
                    compared_messages[-1].get('messages').append(
                        {"role": "assistant", "content": message['content']['text']})
    return compared_messages


# TODO I tried change to ASYNC methods for analyze , but not see different in speed
def analyze_overall_conversation(chats_with_compared_messages: list):
    chats_analyze = []
    for chat in chats_with_compared_messages:  # TODO CLEAR IT
        chat_text = "\n".join([message.get('role') + ": " + message.get('content') for message in chat.get('messages')])
        prompt = f"""
                    Ты - эксперт по клиентскому обслуживанию.
                    Твоя задача - проанализировать переписку между менеджером (assistant) и клиентом (user).
                    Оцени чат целиком с точки зрения качества обслуживания клиента.

                            Формат переписки:
                            - Сначала идет описание роли собеседника, затем его текст
                            - user - это клиент
                            - assistant - это менеджер

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
        chats_analyze.append({
            "chat_id": chat.get('chat_id', None),
            "chat_text": chat.get('messages', None),
            "analysis": completion.choices[0].message.content
        })
    return chats_analyze
