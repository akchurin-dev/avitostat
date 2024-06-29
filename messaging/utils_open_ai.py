import os
import openai
from dotenv import load_dotenv

load_dotenv()
OPENAI_SECRET_KEY = os.getenv('OPENAI_SECRET_KEY')
openai.api_key = OPENAI_SECRET_KEY


def compare_messages_for_ai(chats_with_raw_messages: list):
    compared_messages = []
    for chat in chats_with_raw_messages:
        chat_id = chat.get('id')
        compared_messages.append({'id': chat_id, 'messages': []})
        for message in chat.get('messages')[:10]:
            if message['direction'] == 'in':
                compared_messages[-1].get('messages').append({"role": "user", "content": message['content']['text']})
            elif message['direction'] == 'out':
                compared_messages[-1].get('messages').append({"role": "assistant", "content": message['content']['text']})
    return compared_messages


# Функция для общего анализа переписки
def analyze_overall_conversation(chats_with_compared_messages: list):
    chats_analyze = []
    for chat in chats_with_compared_messages:
        chat_text = "\n".join([message.get('content') + message.get('role') for message in chat.get('messages')])
        prompt = (f"Оцените эту переписку с точки зрения клиентского обслуживания."
                  f"Переписка:\n{chat_text}\n"
                  f"Почему данная переписка может быть плохим примером?")
        response = openai.Completion.create(
            model="gpt-4",
            prompt=prompt,
            max_tokens=500,
            n=1,
            stop=None,
            temperature=0.5
        )
        analysis = response.choices[0].text.strip()
        chats_analyze.append({
            "id": chat.get('id'),
            "analysis": analysis,
        })
    return chats_analyze

# Анализируем переписку в целом
# overall_analysis = analyze_overall_conversation(messages)
# print("Общий анализ переписки:")
# print(overall_analysis)

# from openai import AsyncOpenAI
#
# client = AsyncOpenAI()
#
# response = await client.chat.completions.create(
#             model="gpt-4",
#             messages=messages,
#             tools=functions,
#             temperature=0.0,
#             tool_choice=None
#         )
