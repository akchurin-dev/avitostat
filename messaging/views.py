from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.views import View
from avito_account.models import AvitoAccount
from messaging.utils_duration import get_duration_week_report


class DurationStatisticsView(View):
    async def get(self, request, *args, **kwargs):
        telegram_id = kwargs.get("telegram_id", None)
        avito_account = await sync_to_async(AvitoAccount.objects.filter(telegram_id=telegram_id).last)()
        if avito_account:
            duration_week_report = get_duration_week_report(avito_account)

            if duration_week_report:
                return JsonResponse(status=200, data=duration_week_report, safe=False)
        else:
            return JsonResponse(status=404, data={"error": "Avito account not found"})
