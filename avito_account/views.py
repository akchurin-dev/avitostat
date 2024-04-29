from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from avito_account.api.get_operations import get_statistics_for_range
from avito_account.dao import items_to_db
from avito_account.models import AvitoAccount, ServiceType, Operation
from avito_account.oauth_utils import create_or_update_avito_account


@method_decorator(csrf_exempt, name='dispatch')
class CallbackView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", None)
        if code:
            avito_account = create_or_update_avito_account(code=code)
            items_to_db(avito_account)

            # TODO написать слой, котоырй будет записывать все объявления в БД
            return JsonResponse({"message": "Hello, you will redirect"})
        else:
            return JsonResponse({"message": "Please provide a code"}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class Test(View):
    def get(self, request, *args, **kwargs):
        start_date = "2024-01-01T00:00:00"
        end_date = "2024-01-14T23:59:59"
        avito_account: AvitoAccount = AvitoAccount.objects.filter(id=359794245).last()

        operations = get_statistics_for_range(avito_account.access_token, start_date, end_date)
        if len(operations) > 0:
            for operation in operations:
                service_type, create = ServiceType.objects.get_or_create(
                    service_name=operation.get("serviceName"),
                    service_type=operation.get("serviceType"),
                    service_id=operation.get("serviceId"),
                )

                Operation.objects.create(
                    amount_bonus=operation.get("amountBonus"),
                    amount_rub=operation.get("amountRub"),
                    amount_total=operation.get("amountTotal"),
                    item_id=operation.get("itemId"),
                    name=operation.get("operationName"),
                    type=operation.get("operationType"),
                    service_id=service_type.id,
                    updated_at=operation.get("amountBonus"),
                )

        return JsonResponse(status=200, data={"message": "Test success"})
