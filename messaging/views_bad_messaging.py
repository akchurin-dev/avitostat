from messaging.tasks import bad_messaging_week_report_async
from django.http import JsonResponse
from django.views import View


class BadMessagingWeekReportAllView(View):
    async def get(self, request, *args, **kwargs):
        await bad_messaging_week_report_async.delay()
        return JsonResponse(status=200, data={"success": "Всё прошло успешно"})


class BadMessagingWeekReportIndividualView(View):
    async def get(self, request, *args, **kwargs):
        object_id = kwargs.get('object_id')
        await bad_messaging_week_report_async(only_for_users=[object_id])
        return JsonResponse(status=200, data={"success": "Всё прошло успешно"})
