from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from avito_account.dao import items_to_db
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
        avito_accounts = AvitoAccount.objects.filter(company__is_active=True)
        avito_accounts_ids = [{"avito_account_id": avito_account.id,
                               "telegram_id": avito_account.telegram_id}
                              for avito_account in avito_accounts if avito_account.telegram_id]
        if avito_accounts_ids:
            return JsonResponse(status=200, data=avito_accounts_ids, safe=False)
        else:
            return JsonResponse(status=404, data={"error": "Not found any Avito accounts"})


@method_decorator(csrf_exempt, name='dispatch')
class AvitoAccountByTelegramIdView(View):
    def get(self, request, *args, **kwargs):
        avito_accounts_datas = []
        telegram_id = kwargs.get("telegram_id", None)
        avito_accounts = AvitoAccount.objects.filter(company__is_active=True, telegram_id=telegram_id)
        for avito_account in avito_accounts:
            avito_accounts_datas.append(
                {"avito_account_id": avito_account.id,
                 "telegram_id": avito_account.telegram_id})

        if avito_accounts_datas:
            return JsonResponse(status=200, data=avito_accounts_datas, safe=False)
        else:
            return JsonResponse(status=404, data={"error": "Not found any Avito accounts"})
