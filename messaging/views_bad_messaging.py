from django.http import JsonResponse
from django.views import View

from messaging.tasks import bad_messaging_week_report_async


class BadMessagingWeekReportAllView(View):
    async def get(self, request, *args, **kwargs):
        await bad_messaging_week_report_async()
        return JsonResponse(status=200, data={"success": "Всё прошло успешно"})