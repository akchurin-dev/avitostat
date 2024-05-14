from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from conversion.utils_week_report import get_week_report


@method_decorator(csrf_exempt, name='dispatch')
class WeekReportView(View):
    def get(self, request, *args, **kwargs):
        telegram_id = kwargs.get("telegram_id", None)
        week_report = get_week_report(telegram_id=telegram_id)

        if week_report:
            return JsonResponse(status=200, data=week_report)
