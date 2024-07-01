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
            for message in chat.get('messages')[:10]:
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
    for chat in chats_with_compared_messages[:5]:  # TODO CLEAR IT
        chat_text = "\n".join([message.get('role') + ": " + message.get('content') for message in chat.get('messages')])
        prompt = (f"Оцените этот чат переписки с точки зрения клиентского обслуживания."
                  f"Оценивать надо чат переписки целиком"
                  f"Переписка:\n{chat_text}\n"
                  f"user - это клиент, а assistant - это менеджер"
                  f"сначала идёт всегда описание роли собеседника а затем его текст, будь внимателен"
                  f"Необходимо выявить факты непрофессионального общения со стороны менеджера."
                  f"Или аспекты которые могли бы быть препядствием для продажи услуги/товара"
                  f"Например невовлеченность в сделку, или холодное общение"
                  f"Нежелание помочь клиенту  найти интересующую информацию и тп"
                  f"НЕ БЕРИ в расчёт такие аспекты как - "
                  f"1) то что менеджер просит контактный номер"
                  f"2) игнорируются системные сообщения о запрете перехода в другие месенджеры"
                  f"Замечания должны быть короткими и лаконичными, сильно придираться ненадо")

        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt},
            ],
            temperature=0.5
        )
        chats_analyze.append({
            "chat_id": chat.get('chat_id', None),
            "chat_text": chat.get('messages', None),
            "analysis": completion.choices[0].message.content
        })
    return chats_analyze
