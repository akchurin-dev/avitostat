from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
# from avito_account.dao import items_to_db
from avito_account.models import AvitoAccount
from avito_account.oauth_utils import create_or_update_avito_account


@method_decorator(csrf_exempt, name='dispatch')
class CallbackView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", None)
        if code:
            avito_account = create_or_update_avito_account(code=code)
            # items_to_db(avito_account) # надо сделать всё асинхронно если есть в записи айтемов необходимость
            return JsonResponse({"message": "Hello, you will redirect"})
        else:
            return JsonResponse({"message": "Please provide a code"}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class AvitoAccountListView(View):
    def get(self, request, *args, **kwargs):
        avito_accounts = AvitoAccount.objects.all()
        avito_account_ids = [avito_account.telegram_id for avito_account in avito_accounts if
                              avito_account.telegram_id]
        unique_avito_account_ids = list(set(avito_account_ids))
        if unique_avito_account_ids:
            return JsonResponse(status=200, data=unique_avito_account_ids, safe=False)
        else:
            return JsonResponse(status=404, data={"error": "Not found any Avito accounts"})


@method_decorator(csrf_exempt, name='dispatch')
class AvitoIdsListByTelegramView(View):
    def get(self, request, *args, **kwargs):
        telegram_id = kwargs.get("telegram_id", None)
        avito_accounts = AvitoAccount.objects.filter(telegram_id=telegram_id, company__is_active=True)
        avito_account_ids = [avito_account.id for avito_account in avito_accounts]
        unique_avito_account_ids = list(set(avito_account_ids))
        if avito_account_ids:
            return JsonResponse(status=200, data=unique_avito_account_ids, safe=False)
        else:
            return JsonResponse(status=404, data={"error": "Not found any Avito accounts"})
