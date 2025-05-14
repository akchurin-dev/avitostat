from messaging.bad_mes_report.statistics.total_statistics_utils import grouping_chats_by_managers


async def get_stat_by_criteria_splitted_by_managers(filtered_chats_only_with_text: list):
    grouped_chats = await grouping_chats_by_managers(filtered_chats_only_with_text)

    if len(grouped_chats) > 0:
        for manager_chats in grouped_chats:
            manager_chats["statistics_by_criteria"] = []
            statistics_for_manager = await get_statistics_by_criteria(manager_chats.get("chats"))
            if statistics_for_manager:
                for result in statistics_for_manager:
                    manager_chats.get("statistics_by_criteria").append(result)
            manager_chats.pop("chats")  # DELETE CHATS AFTER CALCULATIONS FOR OPTIMIZATION JSON ON API

    return grouped_chats


async def get_color_description(result: dict, color="#C14D3D", text="плохо"):
    percentage = result.get("positive_chats") / result.get("total_chats")
    if 0.33 >= percentage > 0:
        color = "#C14D3D"
        text = "плохо"
    elif 0.66 >= percentage > 0.33:
        color = "#E4A03B"
        text = "средне"
    elif 1 >= percentage > 0.66:
        color = "#73C356"
        text = "отлично"

    return {
        "text": text,
        "color": color,
    }


async def get_statistics_by_criteria(actual_chats_with_messages: list):
    results = {}

    for chat in actual_chats_with_messages:
        analyze_by_criteria = chat.get("analyze_by_criteria", None)

        if analyze_by_criteria is None:
            continue

        if len(results) == 0:
            for key, value in analyze_by_criteria.items():
                results[key] = {
                    "positive_chats": 0,
                    "total_chats": len(actual_chats_with_messages),
                    "criterion_name": value.get("criterion"),
                    "criterion_id": key,
                }

        for k, v in analyze_by_criteria.items():
            if k in results and v.get("meets_criterion"):
                results[k]["positive_chats"] += 1

        for result in results.values():
            result["description"] = await get_color_description(result)

    result_converted_to_list = list(results.values())
    return result_converted_to_list
