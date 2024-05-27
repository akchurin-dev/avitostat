from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.views import View
from avito_account.models import AvitoAccount
from messaging.api import get_chats, get_chats_messages
from messaging.utils_duration import get_answer_durations, get_chats_for_week, get_duration_statistics


class DurationStatisticsView(View):
    async def get(self, request, *args, **kwargs):
        telegram_id = kwargs.get("telegram_id", None)
        avito_account = await sync_to_async(AvitoAccount.objects.filter(telegram_id=telegram_id).last)()

        if avito_account:
            chats = await get_chats(avito_account)
            if chats:
                actual_chats = await get_chats_for_week(chats)
                actual_chats_with_messages = await get_chats_messages(avito_account, actual_chats)
                durations = await get_answer_durations(actual_chats_with_messages)
                duration_statistics = await get_duration_statistics(durations)
                return JsonResponse(duration_statistics, safe=False)
            else:
                return JsonResponse(status=404, data={"error": "Чаты не найдены"})
        else:
            return JsonResponse(status=404, data={"error": "Аккаунт Avito не найден"})
