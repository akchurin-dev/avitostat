import json
from pprint import pprint

from messaging.bad_mes_report.utils_bad_messaging_report import get_messaging_report_data
from messaging.tasks import bad_messaging_week_report_async, bad_messaging_week_report_async_task
from django.http import JsonResponse
from django.views import View


class BadMessagingWeekReportAllView(View):
    def get(self, request, *args, **kwargs):
        bad_messaging_week_report_async_task.delay()
        return JsonResponse(status=200, data={"success": "Всё прошло успешно"})


class BadMessagingWeekReportIndividualView(View):
    async def get(self, request, *args, **kwargs):
        object_id = kwargs.get('object_id')
        send_report = await bad_messaging_week_report_async(only_for_users=[object_id])
        if send_report is None:
            return JsonResponse(status=404, data={"error": "Ниодного аккаунта по заданным параметрам небыло найдено"})
        else:
            return JsonResponse(status=200, data={"success": "Всё прошло успешно"})


class MonthReportIndividualView(View):
    async def get(self, request, *args, **kwargs):
        avito_account_id = kwargs.get('avito_account_id')
        report_data = await get_messaging_report_data(test_from_prod=False,
                                                      avito_account_id=avito_account_id,
                                                      for_api=True, )

        if report_data is not None:
            serialized_report_data = json.dumps(report_data, ensure_ascii=False, indent=4)
            return JsonResponse(status=404, data=serialized_report_data)
        else:
            return JsonResponse(status=200, data={"success": "Всё прошло успешно"})
