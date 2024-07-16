from django.http import JsonResponse
from django.views import View
from messaging.tasks import bad_messaging_week_report_async


class BadMessagingWeekReportAllView(View):
    async def get(self, request, *args, **kwargs):
        await bad_messaging_week_report_async.delay()
        return JsonResponse(status=200, data={"success": "Всё прошло успешно"})


class BadMessagingWeekReportIndividualView(View):
    #TODO добавить извлечение айдишника из урла и добавление в фильтр
    async def get(self, request, *args, **kwargs):
        await bad_messaging_week_report_async(only_for_users=[203199629, 203199629])
        return JsonResponse(status=200, data={"success": "Всё прошло успешно"})
