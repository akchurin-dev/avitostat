from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from avito_account.api.get_operations import get_active_operations_for_period
from avito_account.models import AvitoAccount
from conversion.api import get_statistics_for_period


@method_decorator(csrf_exempt, name='dispatch')
class Test(View):
    def get(self, request, *args, **kwargs):
        avito_account = AvitoAccount.objects.filter(id=203199629).last()
        statistics = get_statistics_for_period(avito_account, period="week")  # Здесь токен рефрешится если он просрочен
        operations = get_active_operations_for_period(avito_account, period="week")
        conversion = conversion_calculate(statistics=statistics, operations=operations)

        return JsonResponse(status=200, data={"message": "Test success"})
