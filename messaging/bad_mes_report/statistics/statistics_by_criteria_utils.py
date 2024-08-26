from messaging.bad_mes_report.statistics.total_statistics_utils import grouping_chats_by_managers


async def get_statistics_by_criteria_splitted_by_managers(actual_chats_with_messages: list):
    grouped_chats = await grouping_chats_by_managers(actual_chats_with_messages)

    if len(grouped_chats) > 0:
        for manager_chats in grouped_chats:
            manager_chats["statistics_by_criteria"] = []
            statistics_for_manager = await get_statistics_by_criteria(
                actual_chats_with_messages=manager_chats.get("chats"))
            if statistics_for_manager:
                manager_chats.get("statistics_by_criteria").append(statistics_for_manager)

    return grouped_chats


async def get_statistics_by_criteria(actual_chats_with_messages: list):
    statistics_by_criteria = {}
    for chat in actual_chats_with_messages:
        analyze_by_criteria = chat.get("analyze_by_criteria")
        # Initialize counters
        if len(statistics_by_criteria) == 0:
            for key, value in analyze_by_criteria.items():
                statistics_by_criteria[key] = {
                    "positive_chats": 0,
                    "total_chats": len(actual_chats_with_messages),
                    "criterion_name": value.get("criterion"),
                }
        # # Feel positive criteria counter
        for k, v in analyze_by_criteria.items():
            if v.get("meets_criterion"):
                statistics_by_criteria[k]["positive_chats"] += 1

    return statistics_by_criteria
