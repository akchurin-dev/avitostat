import datetime
from typing import Literal

import httpx
from loguru import logger
from pydantic import BaseModel

from tests import config
from utils import httpx_helper


class User(BaseModel):
    id: int


class AvitoAccount(BaseModel):
    id: int
    name: str
    access_token: str
    refresh_token: str
    telegram_id: int | None = None
    created_by_id: int


class AIChatBot(BaseModel):
    id: int


_avitostat_client = httpx_helper.create_client(base_url=config.DJANGO_BASE_URL)


def create_user() -> User:
    action = f"/deep_tests/user"

    response = _request(action=action, method="POST")
    response.raise_for_status()

    return User.model_validate(response.json())


def delete_user(user_id: int):
    action = f"/deep_tests/user/{user_id}"

    response = _request(action=action, method="DELETE")
    response.raise_for_status()


def create_or_update_avito_account(
    access_token: str,
    refresh_token: str,
    telegram_id: str,
    created_by_id: int,
) -> tuple[AvitoAccount, bool]:

    action = f"/deep_tests/avito-account"

    data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "telegram_id": telegram_id,
        "created_by_id": created_by_id,
    }

    response = _request(action=action, method="POST", data=data)
    response.raise_for_status()

    avito_account = AvitoAccount.model_validate(response.json())
    created = response.status_code == 201

    return avito_account, created


def get_avito_account(avito_account_id: int) -> AvitoAccount:
    action = f"/deep_tests/avito-account/{avito_account_id}"

    response = _request(action, "GET")
    response.raise_for_status()

    return AvitoAccount.model_validate(response.json())


def delete_avito_account(avito_account_id: int) -> None:
    action = f"/deep_tests/avito-account/{avito_account_id}"

    response = _request(action, "DELETE")
    response.raise_for_status()


def create_avito_ai_chat_bot(avito_account_id: int, turn_off_after_manager: bool) -> AIChatBot:
    action = f"/deep_tests/avito-ai-chat-bot"

    data = {
        "avito_account": avito_account_id,
        "is_active": True,
        "total_info": "Ты чат бот консультант, твоя задача помогать клиентам",
        "rules": "Общайся вежливо",
        "checkpoints": "помочь клиентам в их вопросах и получить номер телефона",
        "waiting_minutes": 1,
        "shutdown_after_manager": turn_off_after_manager,
        "work_time_from": datetime.time(hour=0, minute=0, second=0),
        "work_time_to": datetime.time(hour=23, minute=59, second=59),
        "statistics_daily_report": False,
        "histories_closed": False,
        "histories_open": False,
    }

    response = _request(action, "POST", data=data)
    response.raise_for_status()

    return AIChatBot.model_validate(response.json())


def delete_avito_ai_chat_bot(ai_chat_bot_id: int) -> None:
    action = f"/deep_tests/avito-ai-chat-bot/{ai_chat_bot_id}"

    response = _request(action, "DELETE")
    response.raise_for_status()


def disable_avito_ai_chat_bot(ai_chat_bot_id: int) -> AIChatBot:
    action = f"/deep_tests/avito-ai-chat-bot/{ai_chat_bot_id}"

    data = {
        "is_active": False,
    }

    response = _request(action, "PATCH", data=data)
    response.raise_for_status()

    return AIChatBot.model_validate(response.json())


def delete_avito_ai_chat_bot_by_avito_account(avito_account_id: int, raise_on_404: bool = True) -> None:
    action = f"/deep_tests/avito-ai-chat-bot-by-avito-account/{avito_account_id}"

    response = _request(action, "DELETE")

    if response.is_success:
        return

    if response.status_code != 404:
        response.raise_for_status()

    if raise_on_404:
        response.raise_for_status()


def set_prev_session_last_avito_message(message_id: str | None) -> None:
    if message_id is None:
        message_id = "-1"

    action = f"/deep_tests/prev-session-last-avito-message?value={message_id}"

    response = _request(action, "PUT")
    response.raise_for_status()


def reset_prev_session_last_avito_message():
    set_prev_session_last_avito_message(None)


def set_use_gpt_flag(value: bool) -> None:
    action = f"/deep_tests/use-gpt-flag?value={value}"

    response = _request(action, "PUT")
    response.raise_for_status()


def delete_avito_chat_bot_tasks(avito_chat_id: str) -> None:
    action = f"/deep_tests/avito-ai-chat-bot-task"

    params = {
        "chat_id": avito_chat_id,
    }

    response = _request(action, "DELETE", params=params)
    response.raise_for_status()


def _request(
    action: str,
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    headers: dict | None = None,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | None = None,
) -> httpx.Response:

    methods = {
        "GET": _avitostat_client.get,
        "POST": _avitostat_client.post,
        "PUT": _avitostat_client.put,
        "PATCH": _avitostat_client.patch,
        "DELETE": _avitostat_client.delete,
    }

    kwargs = {
        "url": action,
        "headers": headers,
        "params": params,
    }

    if method not in ["GET", "DELETE"]:
        kwargs.update({
            "data": data,
            "json": json,
        })

    for _ in range(1000):
        try:
            response: httpx.Response = methods[method](**kwargs)
        except httpx.TimeoutException:
            pass
        else:
            break

    if not response.is_success:
        logger.info((
            f"Not success response when request avitostat '{action}', "
            f"got status={response.status_code}, data={response.text}"
        ))

    return response
