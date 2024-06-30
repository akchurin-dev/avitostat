import datetime
from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.views import View
from avito_account.models import AvitoAccount
from exceptions import HTTPException
from messaging.api import get_chats, get_chats_messages
from messaging.utils_duration import get_answer_durations
from messaging.utils_open_ai import compare_messages_for_ai, analyze_overall_conversation


async def get_chats_for_last_week(chats: list) -> list:
    filtered_chats = []
    now = datetime.datetime.now()

    if len(chats) > 0:
        for chat in chats:
            updated = datetime.datetime.fromtimestamp(chat.get("updated"))
            timedelta = now - updated
            print(timedelta)
            if 7 >= timedelta.days > -1:
                filtered_chats.append(chat)
        return filtered_chats


async def convert_seconds(seconds):
    td = datetime.timedelta(seconds=seconds)
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} д")
    if hours > 0:
        parts.append(f"{hours} ч")
    if minutes > 0:
        parts.append(f"{minutes} м")
    if seconds > 0:
        parts.append(f"{seconds} с")

    return ": ".join(parts)


async def get_duration_statistics(chats: list):
    statistics = {}
    total_sum = sum([chat[0] for chat in chats])
    total_len = len(chats)
    if total_sum > 0 and total_len > 0:
        average_duration = total_sum / total_len
        average_duration_formatted = await convert_seconds(average_duration)
        statistics["average_duration"] = average_duration_formatted

    top_durations = sorted(chats, key=lambda x: x[0])[::-1][:10]
    top_durations_formatted = [[await convert_seconds(duration[0]), duration[1], duration[2]] for duration in
                               top_durations]
    statistics["top_durations"] = top_durations_formatted
    return statistics


class DurationWeekStatisticsView(View):
    async def get(self, request, *args, **kwargs):
        telegram_id = kwargs.get("telegram_id", None)
        avito_account = await sync_to_async(AvitoAccount.objects.filter(telegram_id=telegram_id).last)()

        if avito_account:
            chats = await get_chats(avito_account)
            if chats:
                actual_chats = await get_chats_for_last_week(chats)
                actual_chats_with_messages = await get_chats_messages(avito_account, actual_chats)
                durations = await get_answer_durations(actual_chats_with_messages)
                duration_statistics = await get_duration_statistics(durations)
                return JsonResponse(duration_statistics, safe=False)
            else:
                return JsonResponse(status=404, data={"error": "Чаты не найдены"})
        else:
            return JsonResponse(status=404, data={"error": "Аккаунт Avito не найден"})


class BadMessagingWeekReportView(View):
    async def get(self, request, *args, **kwargs):
        analyze_all_chats = []
        avito_accounts_id = kwargs.get("avito_accounts_id", None)
        avito_account = await sync_to_async(AvitoAccount.objects.filter(id=avito_accounts_id).last)()
        if avito_account:
            chats = await get_chats(avito_account)
            # ADD RESULTS
            analyze_all_chats.append({
                "avito_account_name": avito_account.name,
                "avito_account_id": avito_account.id,
            })
            if chats:  # 5 lines down duplicated from DurationWeekStatisticsView
                actual_chats = await get_chats_for_last_week(chats)
                actual_chats_with_messages = await get_chats_messages(avito_account, actual_chats)
                compared_messages = compare_messages_for_ai(actual_chats_with_messages)
                analyze = analyze_overall_conversation(compared_messages)
                if analyze:
                    analyze_all_chats[-1]["analyze"] = analyze
            else:
                analyze_all_chats[-1]["compared_messages"] = "Чаты не найдены 404"
            return JsonResponse(analyze_all_chats, safe=False)
        else:
            return JsonResponse(status=404, data={"error": "Аккаунт Avito не найден"})
