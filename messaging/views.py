from messaging.bad_mes_report.utils_bad_messaging_report import get_messaging_report_data
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
    async def get(self, request, *args, **kwargs):
        avito_account_id = kwargs.get('avito_account_id')
        report_data = get_messaging_report_data_async_task.delay(
            test_from_prod=False,
            avito_account_id=avito_account_id,
            for_api=True,
        )

        chats = report_data.get("chats", None)
        if chats is not None:
            for chat in chats:
                messages = chat.get("messages", None)
                if len(messages) > 15:
                    chat["messages"] = messages[:15]

        if report_data is not None:
            # Используем кастомный JSON-энкодер для сериализации
            serialized_report_data = json.dumps(report_data, ensure_ascii=False, indent=4, cls=CustomJSONEncoder)
            return JsonResponse(status=200, data=json.loads(serialized_report_data))  # Преобразуем обратно в Python-объект
        else:
            return JsonResponse(status=404, data={"error": "Данные не найдены"})

