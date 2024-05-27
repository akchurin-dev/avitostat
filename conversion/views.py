from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from avito_account.models import AvitoAccount
from conversion.utils_week_report import get_conversion_week_report


@method_decorator(csrf_exempt, name='dispatch')
class WeekReportView(View):
    def get(self, request, *args, **kwargs):
        telegram_id = kwargs.get("telegram_id", None)
        avito_account = AvitoAccount.objects.filter(telegram_id=telegram_id).last()
        if avito_account:
            week_report = get_conversion_week_report(avito_account=avito_account)

            if week_report:
                return JsonResponse(status=200, data=week_report)
        else:
            return JsonResponse(status=404, data={"error": "Avito account not found"})
