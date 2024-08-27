from messaging.bad_mes_report.statistics.total_statistics_utils import grouping_chats_by_managers


async def get_statistics_by_criteria_splitted_by_managers(filtered_chats_only_with_text: list):
    grouped_chats = await grouping_chats_by_managers(filtered_chats_only_with_text)

    if len(grouped_chats) > 0:
        for manager_chats in grouped_chats:
            manager_chats["statistics_by_criteria"] = []
            statistics_for_manager = await get_statistics_by_criteria(manager_chats.get("chats"))
            if statistics_for_manager:
                for result in statistics_for_manager:
                    manager_chats.get("statistics_by_criteria").append(result)

    return grouped_chats


async def get_statistics_by_criteria(actual_chats_with_messages: list):
    result = {}
    for chat in actual_chats_with_messages:
        analyze_by_criteria = chat.get("analyze_by_criteria", None)
        # Initialize counters
        if analyze_by_criteria is not None:
            if len(result) == 0:
                for key, value in analyze_by_criteria.items():
                    result[key] = {
                        "positive_chats": 0,
                        "total_chats": len(actual_chats_with_messages),
                        "criterion_name": value.get("criterion"),
                        "criterion_id": key,
                    }
            # # Feel positive criteria counter
            for k, v in analyze_by_criteria.items():
                if v.get("meets_criterion"):
                    result[k]["positive_chats"] += 1

    result_converted_to_list = list(result.values())
    return result_converted_to_list
