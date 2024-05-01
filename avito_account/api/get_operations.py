from datetime import datetime, timedelta
import requests

from avito_account.models import AvitoAccount


def operations(access_token: str, start_date: str, end_date: str) -> dict:
    url = "https://api.avito.ru/core/v1/accounts/operations_history/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    params = {
        "dateTimeFrom": start_date,
        "dateTimeTo": end_date
    }

    response = requests.post(url, headers=headers, json=params)
    response.raise_for_status()

    return response.json()


def get_operations_splitted_by_week(access_token: str, start_date: str, end_date: str) -> dict:
    # Максимальный период для запроса - не более одной недели
    if (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days > 7:
        raise ValueError("Period should not exceed 7 days")

    return operations(access_token, start_date, end_date)


def get_operations_for_period(avito_account: AvitoAccount, period: str) -> list:
    valid_periods = ['month', 'week', 'day']
    if period not in valid_periods:
        raise ValueError("Invalid period. Please choose from 'month', 'week', or 'day'.")

    # Определяем диапазон дат в зависимости от выбранного периода
    today = datetime.now()
    date_to = today.strftime("%Y-%m-%d")
    if period == 'month':
        date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    elif period == 'week':
        date_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    else:  # Период 'day'
        date_from = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    # Разбиваем заданный период на отрезки по 7 дней
    current_start = datetime.fromisoformat(date_from)
    end_date_dt = datetime.fromisoformat(date_to)
    current_end = min(current_start + timedelta(days=7), end_date_dt)
    all_statistics = {}

    while current_start < end_date_dt:
        # Получаем статистику для текущего отрезка
        statistics = get_operations_splitted_by_week(avito_account.access_token, current_start.isoformat(),
                                                     current_end.isoformat())
        # Обновляем словарь статистики
        all_statistics[current_start.isoformat()] = statistics

        # Переходим к следующему отрезку
        current_start = current_end
        current_end = min(current_start + timedelta(days=7), end_date_dt)

    operations_splitted_by_weeks = [item[1].get("result").get("operations") for item in all_statistics.items()]
    operations_list = []
    for week in operations_splitted_by_weeks:
        operations_list.extend(week)
    return operations_list
