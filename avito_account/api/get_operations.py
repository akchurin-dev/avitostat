from datetime import datetime, timedelta
from pprint import pprint
import requests


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


def get_operations_for_period(access_token: str, start_date: str, end_date: str) -> dict:
    # Максимальный период для запроса - не более одной недели
    if (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days > 7:
        raise ValueError("Period should not exceed 7 days")

    return operations(access_token, start_date, end_date)


def get_operations_for_range(access_token: str, start_date: str, end_date: str) -> list:
    # Разбиваем заданный период на отрезки по 7 дней
    current_start = datetime.fromisoformat(start_date)
    end_date_dt = datetime.fromisoformat(end_date)
    current_end = min(current_start + timedelta(days=7), end_date_dt)
    all_statistics = {}

    while current_start < end_date_dt:
        # Получаем статистику для текущего отрезка
        statistics = get_operations_for_period(access_token, current_start.isoformat(), current_end.isoformat())
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
