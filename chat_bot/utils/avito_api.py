from collections.abc import Generator
from datetime import date
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel
from pydantic import Field
from pydantic import TypeAdapter

from avito_account.models.models import AvitoAccount
from base import settings
from utils import httpx_helper
from utils.logging import TraceLogger


class Balance(BaseModel):
    bonus: float
    real: float


class OperationType(Enum):
        CREDIT_WRITE_OFF = "списание в счёт кредита"
        POSTPAYMENT = "постоплата"
        CPA_ADVANCE_DEPOSIT = "внесение CPA аванса"
        CPA_ADVANCE_REFUND = "возврат CPA аванса"
        ADVANCE = "аванс"
        ADVANCE_REFUND = "возврат аванса"
        WALLET_WRITE_OFF = "списание средств с кошелька в доход (не за оказанные услуги)"
        BONUS_BURN = "сжигание бонусов"
        AUTO_STRATEGY_RESERVATION = "резервирование под автостратегию"
        AUTO_STRATEGY_RESERVATION_REFUND = "возврат зарезервированных средств под автостатегию на кошелек"
        SERVICE_RESERVATION = "резервирование средств под услугу"
        SERVICE_RESERVATION_REFUND = "возврат зарзервированных средств на баланс кошелька"
        REVENUE_RECOGNITION = "признание выручки"
        BALANCE_WRITE_OFF = "списание остатка"
        STORNO = "сторно"
        PROTESTED = "опротестовано"
        CHARGEBACK = "чарджбэк"


class ServiceType(Enum):
    VAS = "vas"
    PERF_VAS = "perf_vas"
    LF = "lf"
    CV = "cv"
    TARIFF = "tariff"
    SUBSCRIPTION = "subscription"
    CPA = "cpa"
    BUNDLE = "bundle"


class Operation(BaseModel):
    amount_bonus: float = Field(alias="amountBonus")
    amount_rub: float = Field(alias="amountRub")
    amount_total: float = Field(alias="amountTotal")
    item_id: int = Field(alias="itemId")
    operation_name: str = Field(alias="operationName")
    operation_type: OperationType = Field(alias="operationType")
    paid_at: datetime | None = Field(alias="paidAt", default=None)
    service_id: int = Field(alias="serviceId")
    service_name: str = Field(alias="serviceName")
    service_type: ServiceType = Field(alias="serviceType")
    updated_at: datetime = Field(alias="updatedAt")


class ItemStatus(Enum):
    ACTIVE = "active"
    REMOVED = "removed"
    OLD = "old"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    NOT_FOUND = "not_found"
    ANOTHER_USER = "another_user"


class VasId(Enum):
    VIP = "vip"
    HIGHLIGHT = "highlight"
    PUSHUP = "pushup"
    PREMIUM = "premium"
    XL = "xl"


class ItemVas(BaseModel):
    finish_time: datetime | None
    schedule: list[datetime] | None
    vas_id: VasId


class Item(BaseModel):
    autoload_item_id: str | None
    finish_time: datetime | None
    start_time: datetime | None
    status: ItemStatus
    url: str | None
    vas: list[ItemVas] | None


class ItemCategory(BaseModel):
    id: int
    name: str


class ItemResource(BaseModel):
    address: str
    category: ItemCategory
    id: int
    price: int | None
    status: ItemStatus
    title: str
    url: str | None


class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    LINK = "link"
    ITEM = "item"
    LOCATION = "location"
    CALL = "call"
    DELETED = "deleted"
    VOICE = "voice"
    SYSTEM = "system"


class MessageDirection(Enum):
    IN = "in"
    OUT = "out"


class MessageVoiceContent(BaseModel):
    voice_id: str


class MessageImageContent(BaseModel):
    size_url_pairs: dict[str, str] = Field(alias="sizes")


class MessageContent(BaseModel):
    text: str | None = None
    voice: MessageVoiceContent | None = None
    image: MessageImageContent | None = None


class BaseMessage(BaseModel):
    id: str
    type: MessageType
    direction: MessageDirection
    created_timestamp: int = Field(alias="created")
    content: MessageContent


class WebhookSubscription(BaseModel):
    url: str
    version: str


class ItemStatistic(BaseModel):
    date: datetime
    unique_contacts: int = Field(alias="uniqContacts")
    unique_favorites: int = Field(alias="uniqFavorites")
    unique_views: int = Field(alias="uniqViews")


class ItemInStatistic(BaseModel):
    item_id: int
    stats: ItemStatistic


class ChatMessage(BaseMessage):
    author_id: int


class ChatUser(BaseModel):
    id: int
    name: str


class Chat(BaseModel):
    id: str
    created_at_timestamp: int = Field(alias="created")
    updated_at_timestamp: int = Field(alias="updated")
    last_message: ChatMessage
    users: list[ChatUser]


class CallsStatisticItemDay(BaseModel):
    answered: int
    calls: int
    date: date
    new: int
    new_answered: int = Field(alias="newAnswered")


class CallsStatisticItem(BaseModel):
    item_id: int = Field(alias="itemId")
    employee_id: int = Field(alias="employeeId")
    days: list[CallsStatisticItemDay]


def get_balance(account: AvitoAccount, *, tlogger: TraceLogger) -> Balance:
    """ https://developers.avito.ru/api-catalog/user/documentation#operation/getUserBalance """

    action = f"/core/v1/accounts/{account.pk}/balance/"

    response = avito_api_request("GET", action, account, tlogger=tlogger)
    response.raise_for_status()

    return Balance.model_validate_json(response.content)


def get_operations_history(account: AvitoAccount, start_date: str, end_date: str, *, tlogger: TraceLogger) -> list[Operation]:
    """ https://developers.avito.ru/api-catalog/user/documentation#operation/postOperationsHistory """

    action = "/core/v1/accounts/operations_history/"

    params = {
        "dateTimeFrom": start_date,
        "dateTimeTo": end_date
    }

    response = avito_api_request("POST", action, account, params=params, tlogger=tlogger)
    response.raise_for_status()

    return TypeAdapter(list[Operation]).validate_python(response.json()["result"]["operations"])


def get_item_info(account: AvitoAccount, item_id: int, *, tlogger: TraceLogger) -> Item:
    """ https://developers.avito.ru/api-catalog/item/documentation#operation/getItemInfo """

    action= f"/core/v1/accounts/{account.pk}/items/{item_id}/"

    response = avito_api_request("GET", action, account, tlogger=tlogger)
    response.raise_for_status()

    return Item.model_validate_json(response.content)


def get_items_list(account: AvitoAccount, *, tlogger: TraceLogger) -> Generator[ItemResource, Any, None]:
    page = 1

    while True:
        resources: list[ItemResource] = get_items_list_page(account, page, per_page=100, tlogger=tlogger)

        if len(resources) == 0:
            return

        for resource in resources:
            yield resource

        page += 1


def get_items_list_page(account: AvitoAccount, page: int, per_page: int = 100, *, tlogger: TraceLogger) -> list[ItemResource]:
    """ https://developers.avito.ru/api-catalog/item/documentation#operation/getItemsInfo """

    action = "/core/v1/items"

    params = {
        "per_page": per_page,
        "status": "active",
        "page": page,
    }

    response = avito_api_request("GET", action, account, params, tlogger=tlogger)
    response.raise_for_status()

    return TypeAdapter(list[ItemResource]).validate_python(response.json().get("resources", []))


def send_message(account: AvitoAccount, chat_id: str, message: str, *, tlogger: TraceLogger) -> BaseMessage:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/postSendMessage """

    action = f"/messenger/v1/accounts/{account.pk}/chats/{chat_id}/messages"

    payload = {
        "message": {
            "text": message,
        },
        "type": "text",
    }

    response = avito_api_request("POST", action, account, json=payload, tlogger=tlogger)
    response.raise_for_status()

    return BaseMessage.model_validate_json(response.content)


def read_chat(account: AvitoAccount, chat_id: str, *, tlogger: TraceLogger) -> bool:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/chatRead """

    action = f"/messenger/v1/accounts/{account.pk}/chats/{chat_id}/read"

    response = avito_api_request("POST", action, account, tlogger=tlogger)
    response.raise_for_status()

    return response.json()["ok"]


def subscribe_for_messages(account: AvitoAccount, *, tlogger: TraceLogger) -> bool:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/postWebhookV3 """

    action = "/messenger/v3/webhook"

    request_data = {"url": settings.AVITO_WEBHOOK_URL}

    response = avito_api_request("POST", action, account, json=request_data, tlogger=tlogger)
    response.raise_for_status()

    if not response.text:
        return False

    return response.json()["ok"]


def unsubscribe_from_messages(account: AvitoAccount, *, tlogger: TraceLogger) -> bool:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/postWebhookUnsubscribe """

    action = "/messenger/v1/webhook/unsubscribe"

    request_data = {"url": settings.AVITO_WEBHOOK_URL}

    response = avito_api_request("POST", action, account, json=request_data, tlogger=tlogger)
    response.raise_for_status()

    if not response.text:
        return False

    return response.json()["ok"]


def get_subscriptions(account: AvitoAccount, *, tlogger: TraceLogger) -> list[WebhookSubscription]:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/getSubscriptions """

    action = "/messenger/v1/subscriptions"

    response = avito_api_request("POST", action, account, tlogger=tlogger)
    response.raise_for_status()

    return TypeAdapter(list[WebhookSubscription]).validate_python(response.json()["subscriptions"])


def get_items_statistic(
    account: AvitoAccount,
    items_ids: list[int],
    period: str,
    since: date,
    until: date,
    *,
    tlogger: TraceLogger
) -> list[ItemInStatistic]:
    """ https://developers.avito.ru/api-catalog/item/documentation#operation/itemStatsShallow """

    action = f"/stats/v1/accounts/{account.pk}/items"

    request_data = {
        'dateFrom': since.isoformat(),
        'dateTo': until.isoformat(),
        'itemIds': items_ids,
        'periodGrouping': period,
    }

    response = avito_api_request("POST", action, account, json=request_data, tlogger=tlogger)
    response.raise_for_status()

    return TypeAdapter(list[ItemInStatistic]).validate_python(response.json()["result"]["items"])


def get_chats(account: AvitoAccount) -> Generator[Chat, Any, None]:
    limit = 50
    offset = 0

    while True:
        chats = get_chat_list_page(account, offset, limit, tlogger=TraceLogger())

        if len(chats) == 0:
            return

        for chat in chats:
            yield chat

        offset += 50


def get_chat_list_page(account: AvitoAccount, offset: int, limit: int = 50, *, tlogger: TraceLogger) -> list[Chat]:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/getChatsV2 """

    action = f"/messenger/v2/accounts/{account.pk}/chats"

    params = {
        "unread_only": False,
        "limit": limit,
        "offset": offset,
    }

    response = avito_api_request("GET", action, account, params=params, tlogger=tlogger)
    response.raise_for_status()

    return TypeAdapter(list[Chat]).validate_python(response.json()["chats"])


def get_chat(account: AvitoAccount, chat_id: str, *, tlogger: TraceLogger) -> Chat:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/getChatByIdV2 """

    action = f"/messenger/v2/accounts/{account.pk}/chats/{chat_id}"

    response = avito_api_request("GET", action, account, tlogger=tlogger)
    response.raise_for_status()

    return Chat.model_validate_json(response.content)


def get_messages_page(
    account: AvitoAccount,
    chat_id: str,
    offset: int,
    limit: int = 50,
    *,
    tlogger: TraceLogger,
) -> list[ChatMessage]:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/getMessagesV3 """

    action = f"/messenger/v3/accounts/{account.pk}/chats/{chat_id}/messages/"

    params = {
        "limit": limit,
        "offset": offset,
    }

    response = avito_api_request(
        method="GET",
        action=action,
        account=account,
        params=params,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return TypeAdapter(list[ChatMessage]).validate_python(response.json()["messages"])


def get_calls_statistic_last_week(
    account: AvitoAccount,
    since: date,
    until: date,
    items_ids: list[int] | None = None,
    *,
    tlogger: TraceLogger,
) -> list[CallsStatisticItem]:
    """ https://developers.avito.ru/api-catalog/item/documentation#operation/postCallsStats """

    action = f"/core/v1/accounts/{account.pk}/calls/stats/"

    request_data: dict[str, Any] = {
        "dateFrom": since.isoformat(),
        "dateTo": until.isoformat(),
    }

    if items_ids is not None:
        request_data["itemIds"] = items_ids

    response = avito_api_request("POST", action, account, json=request_data, tlogger=tlogger)
    response.raise_for_status()

    return TypeAdapter(list[CallsStatisticItem]).validate_python(response.json()["result"]["items"])


def get_voice_id_url_pairs(account: AvitoAccount, voices_ids: list[str], *, tlogger: TraceLogger) -> dict[str, str]:
    """ https://developers.avito.ru/api-catalog/messenger/documentation#operation/getVoiceFiles """

    action = f"/messenger/v1/accounts/{account.pk}/getVoiceFiles"

    params = {"voice_ids": voices_ids}

    response = avito_api_request(
        method="GET",
        action=action,
        account=account,
        params=params,
        tlogger=tlogger,
    )
    response.raise_for_status()

    return response.json()["voices_urls"]


def avito_api_request(
    method: httpx_helper.MethodType,
    action: str,
    account: AvitoAccount,
    params: dict | None = None,
    data: dict | None = None,
    json: dict | list | None = None,
    headers: dict | None = None,
    *,
    tlogger: TraceLogger,
):
    url = "https://api.avito.ru" + action

    assert account.access_token
    headers = httpx_helper.add_bearer(headers, account.access_token)
    headers = httpx_helper.add_header(headers, "Content-Type", "application/json")

    response = httpx_helper.request(
        method=method,
        url=url,
        params=params,
        data=data,
        json=json,
        headers=headers,
        tlogger=tlogger,
    )

    # if token expired:
    #   update token
    #   retry request

    return response
