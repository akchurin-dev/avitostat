from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from avito_account.models import AvitoAccount
from conversion.utils_week_report import get_week_report
from exceptions import HTTPException


@method_decorator(csrf_exempt, name='dispatch')
class WeekReportView(View):
    async def get(self, request, *args, **kwargs):
        avito_account_id = kwargs.get("avito_account_id", None)
        avito_account = await sync_to_async(AvitoAccount.objects.filter(id=avito_account_id).last)()
        if avito_account:
            await avito_account.update_refresh_token_async()
            try:
                week_report = await get_week_report(avito_account=avito_account)
                return JsonResponse(status=200, data=week_report)
            except HTTPException as e:
                return JsonResponse(status=e.status_code, data={"error": e.detail})
        else:
            return JsonResponse(status=404, data={"error": "Avito account not found"})

