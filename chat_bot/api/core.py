from avito_account import avito_api
from avito_account.models.models import AvitoAccount


async def send_message_to_avito(avito_account: AvitoAccount, user_id: int, chat_id: str, message: str):
    action = f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages"
    headers = {
        "Authorization": f"Bearer {avito_account.access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "message": {
            "text": message,
        },
        "type": "text"
    }

    response = avito_api.client.post(action, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


async def read_chat(avito_account: AvitoAccount, user_id: int, chat_id: str):
    action = f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/read"
    headers = {
        "Authorization": f"Bearer {avito_account.access_token}",
    }

    response = avito_api.client.post(action, headers=headers)
    response.raise_for_status()
    return response.json()

class AvitoMessengerSync:
    @staticmethod
    def send_message_to_avito(avito_account: AvitoAccount, user_id: int, chat_id: str, message: str):
        action = f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/messages"
        headers = {
            "Authorization": f"Bearer {avito_account.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "message": {
                "text": message,
            },
            "type": "text"
        }

        response = avito_api.client.post(action, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def read_chat(avito_account: AvitoAccount, user_id: int, chat_id: str):
        action = f"/messenger/v1/accounts/{user_id}/chats/{chat_id}/read"
        headers = {
            "Authorization": f"Bearer {avito_account.access_token}",
        }

        response = avito_api.client.post(action, headers=headers)
        response.raise_for_status()
        return response.json()
