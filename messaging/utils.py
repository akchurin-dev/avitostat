from datetime import datetime
from typing import Dict, Any, List


async def get_answer_durations(chats: List[Dict[str, Any]]) -> Dict[Any, Any]:
    duration_times = {}

    for chat in chats:
        messages = chat.get("messages")
        last_in_message = None

        for message in messages:
            if message['direction'] == 'in':
                last_in_message = message
            elif message['direction'] == 'out' and last_in_message:
                in_time = datetime.fromtimestamp(last_in_message['created'])
                out_time = datetime.fromtimestamp(message['created'])
                duration = (out_time - in_time).total_seconds()

                chat_id = chat.get('id')
                message_id = message.get('id')
                if chat_id not in duration_times:
                    duration_times[chat_id] = {}
                duration_times[chat_id][message_id] = duration

                last_in_message = None

    return duration_times
