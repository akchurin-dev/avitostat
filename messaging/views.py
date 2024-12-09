from messaging.models import ReportMonth
from messaging.tasks import bad_messaging_week_report_async, bad_messaging_week_report_async_task, \
    get_messaging_report_data_async_task
import json
from datetime import datetime, time
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


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, time)):
            return obj.isoformat()  # Преобразование в строку формата ISO 8601
        return super().default(obj)


class MonthReportIndividualView(View):
    def get(self, request, *args, **kwargs):
        avito_account_id = kwargs.get('avito_account_id')
        current_month = datetime.now().month
        report = ReportMonth.objects.filter(account_id=avito_account_id,
                                            month=current_month,
                                            ).last()
        if report is not None:
            return JsonResponse(status=200, data=report.data, safe=False)
        else:
            return JsonResponse(status=404, data={"error": "Данные не найдены"})

