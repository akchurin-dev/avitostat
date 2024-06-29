import openai
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
        compared_messages.append({'id': chat_id, 'messages': []})
        for message in chat.get('messages')[:10]:
            if message['direction'] == 'in':
                compared_messages[-1].get('messages').append({"role": "user", "content": message['content']['text']})
            elif message['direction'] == 'out':
                compared_messages[-1].get('messages').append(
                    {"role": "assistant", "content": message['content']['text']})
    return compared_messages


# Функция для общего анализа переписки
def analyze_overall_conversation(chats_with_compared_messages: list):
    chats_analyze = []
    for chat in chats_with_compared_messages[:5]:     #TODO CLEAR THIS
        chat_text = "\n".join([message.get('content') + message.get('role') for message in chat.get('messages')])
        prompt = (f"Оцените эту переписку с точки зрения клиентского обслуживания."
                  f"Переписка:\n{chat_text}\n"
                  f"Необходимо выявить факты непрофессионального общения со стороны менеджера."
                  f"Например невовлеченность в сделку, или холодное общение"
                  f"Нежелание помочь клиенту  найти интересующую информацию и тп"
                  f"НЕ БЕРИ в расчёт такие аспекты как - "
                  f"1) то что менеджер просит контактный номер"
                  f"2) игнорируются системные сообщения о запрете перехода в другие месенджеры"
                  f"Почему данная переписка может быть плохим примером?")

        ### NEW GENERATION
        prompt_with_chats = prompt + f"вот сама переписка - {chat_text}"
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": prompt_with_chats},
            ],
            temperature=0.5
        )
        chats_analyze.append({
            "id": chat.get('id'),
            "analysis": completion.choices[0].message.content
        })
    return chats_analyze
