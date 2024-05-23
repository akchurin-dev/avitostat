import datetime
from datetime import timezone

from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.views import View

from avito_account.models import AvitoAccount
from messaging.api import get_chats, get_chats_messages


async def get_chats_for_week(chats: list) -> list:
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


class ChatListView(View):
    async def get(self, request, *args, **kwargs):
        telegram_id = kwargs.get("telegram_id", None)
        avito_account = await sync_to_async(AvitoAccount.objects.filter(telegram_id=telegram_id).last)()

        if avito_account:
            chats = await get_chats(avito_account)
            if chats:
                actual_chats = await get_chats_for_week(chats)
                actual_chats_with_messages = await get_chats_messages(avito_account, actual_chats)
                return JsonResponse(actual_chats_with_messages, safe=False)
            else:
                return JsonResponse(status=404, data={"error": "Чаты не найдены"})
        else:
            return JsonResponse(status=404, data={"error": "Аккаунт Avito не найден"})
