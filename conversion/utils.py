from datetime import datetime, timedelta


def dates_for_period(period: str):
    valid_periods = ['month', 'week', 'day']
    if period not in valid_periods:
        raise ValueError("Invalid period. Please choose from 'month', 'week', or 'day'.")

    today = datetime.now()
    date_to = today.strftime("%Y-%m-%d")
    if period == 'month':
        date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    elif period == 'week':
        date_from = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    else:  # Период 'day'
        date_from = (today - timedelta(days=1)).strftime("%Y-%m-%d")

    return date_from, date_to
