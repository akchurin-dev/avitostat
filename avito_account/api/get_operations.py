import re
import httpx
from datetime import datetime, timedelta
import pytz
from asgiref.sync import sync_to_async

from avito_account.models.excluded_items import ExcludedItem
from avito_account.models.models import AvitoAccount
from conversion.utils import dates_for_period_with_extra_reserve, active_services_for_period_filtering
from base.exceptions import HTTPException


async def operations(access_token: str, start_date: str, end_date: str) -> dict:
    url = "https://api.avito.ru/core/v1/accounts/operations_history/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {
        "dateTimeFrom": start_date,
        "dateTimeTo": end_date
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=params)

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


async def get_operations_splitted_by_week(access_token: str, start_date: str, end_date: str) -> dict:
    # Максимальный период для запроса - не более одной недели
    if (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days > 7:
        raise ValueError("Period should not exceed 7 days")

    return await operations(access_token, start_date, end_date)


async def add_custom_calculations(operations_list: list) -> list:
    moscow_tz = pytz.timezone('Europe/Moscow')
    current_date = datetime.now(moscow_tz)
    for operation in operations_list:
        updated_at = operation.get('updatedAt')
        date = datetime.fromisoformat(updated_at)
        if operation.get('serviceId') == 111:
            pattern = r'\d+'
            amount, duration = re.findall(pattern, operation.get('operationName'))
            finish_at = date + timedelta(days=int(duration))

            days_left = (finish_at - current_date).days

            operation |= {
                'amount_per_day': operation.get('amountRub') / int(duration),
                'duration': int(duration),
                'finishAt': finish_at.isoformat(),
            }
            if days_left and days_left > 0:
                operation |= {
                    'days_left_active_total': days_left,
                }

        elif operation.get('serviceId') == 16:
            finish_at = date + timedelta(days=7)
            days_left = (finish_at - current_date).days
            operation |= {
                'amount_per_day': operation.get('amountRub') / 7,
                'duration_days': 7,
                'finishAt': finish_at.isoformat(),
                'days_left_active': days_left,
            }
            if days_left and days_left > 0:
                operation |= {
                    'days_left_active_total': days_left,
                }
        # TODO проверку на наличие новых айдишников услуг куда то логировать
    return operations_list


async def get_active_operations_for_period(avito_account: AvitoAccount, period: str) -> list:
    date_from, date_to = await dates_for_period_with_extra_reserve(period=period)

    # Разбиваем заданный период на отрезки по 7 дней
    current_start = datetime.fromisoformat(date_from)
    end_date_dt = datetime.fromisoformat(date_to)
    current_end = min(current_start + timedelta(days=7), end_date_dt)
    all_statistics = {}

    while current_start < end_date_dt:
        # Получаем статистику для текущего отрезка
        statistics = await get_operations_splitted_by_week(avito_account.access_token, current_start.isoformat(),
                                                           current_end.isoformat())
        # Обновляем словарь статистики
        all_statistics[current_start.isoformat()] = statistics

        # Переходим к следующему отрезку
        current_start = current_end
        current_end = min(current_start + timedelta(days=7), end_date_dt)

    operations_splitted_by_weeks = [item[1] for item in all_statistics.items() if
                                    item[1] is not None]  # Исключаем все пустые данные об операциях

    operations_splitted_by_weeks = [item.get("result").get("operations") for item in operations_splitted_by_weeks]
    operations_list = []
    for week in operations_splitted_by_weeks:
        operations_list.extend(week)

    operations_list_with_calculations = await add_custom_calculations(operations_list)
    active_operations = await active_services_for_period_filtering(period=period,
                                                                   operations=operations_list_with_calculations)

    active_operations = await operations_filter_excluded_items(active_operations, avito_account)

    return active_operations


async def operations_filter_excluded_items(active_operations, avito_account) -> list:
    filtered_operations = []
    excluded_items = await sync_to_async(list)(ExcludedItem.objects.filter(avito_account_id=avito_account.id))
    excluded_ids = [item.id for item in excluded_items]

    for operation in active_operations:
        if operation.get("'itemId'") not in excluded_ids:
            filtered_operations.append(operation)

    return filtered_operations