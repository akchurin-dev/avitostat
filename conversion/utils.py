from datetime import datetime, timedelta


async def dates_for_period_with_extra_reserve(period: str):
    valid_periods = ['month', 'week', 'day']
    if period not in valid_periods:
        raise ValueError("Invalid period. Please choose from 'month', 'week', or 'day'.")

    today = datetime.now()
    date_to = today.strftime("%Y-%m-%d")
    if period == 'month':
        date_from = (today - timedelta(days=60)).strftime("%Y-%m-%d")
    elif period == 'week':
        date_from = (today - timedelta(days=37)).strftime("%Y-%m-%d")
    else:  # period is 'day'
        date_from = (today - timedelta(days=31)).strftime("%Y-%m-%d")

    return date_from, date_to


async def dates_for_period_without_extra_reserve(period: str):
    valid_periods = ['month', 'week', 'day']
    if period not in valid_periods:
        raise ValueError("Invalid period. Please choose from 'month', 'week', or 'day'.")

    date_to = datetime.now()
    if period == 'month':
        date_from = (date_to - timedelta(days=29))
    elif period == 'week':
        date_from = (date_to - timedelta(days=6))
    else:  # Period is 'day'
        date_from = (date_to - timedelta(days=1))
    return date_from, date_to


async def active_services_for_period_filtering(period: str, operations: list) -> list:
    active_services = []
    date_from, date_to = await dates_for_period_without_extra_reserve(period=period)

    for operation in operations:
        service_start = operation.get("updatedAt")
        service_end = operation.get("finishAt")

        if service_start and service_end:
            # Convert string dates to datetime objects
            service_start = datetime.fromisoformat(service_start).replace(tzinfo=None)
            service_end = datetime.fromisoformat(service_end).replace(tzinfo=None)
            # Check for period overlap
            if date_to <= service_start or date_from >= service_end:
                continue

            # Find the overlap period
            intersection_start = max(date_from, service_start)
            intersection_end = min(date_to, service_end)

            # Calculate the difference in days
            active_days = (intersection_end - intersection_start).days + 1

            # If there are active days, add the service to the list
            if active_days > 0:
                operation |= {
                    "period_days_active": active_days,
                    "period_coast": active_days * operation.get("amount_per_day"),
                }
                active_services.append(operation)

    return active_services
