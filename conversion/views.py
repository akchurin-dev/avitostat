from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from avito_account.api.get_operations import get_operations_for_period
from avito_account.models import AvitoAccount
from conversion.api import get_statistics_for_period


# Create your views here.
@method_decorator(csrf_exempt, name='dispatch')
class Test(View):
    def get(self, request, *args, **kwargs):
        avito_account = AvitoAccount.objects.filter(id=203199629).last()
        statistics = get_statistics_for_period(avito_account, period="week")  # Здесь токен рефрешится если он просрочен
        operations_for_week = get_operations_for_period(avito_account, period="week")
        # TODO операции - те, срок действия которых не истёк на указанный период, а не те что были оплачены в этот период
        # TODO соответственно могли быть операции намного раньше но на учетный период они еще активны
        print(123)
        return JsonResponse(status=200, data={"message": "Test success"})
