from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from avito_account.API_avito import get_items_list
from avito_account.oauth_utils import create_or_update_avito_account


@method_decorator(csrf_exempt, name='dispatch')
class CallbackView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", None)
        if code:
            avito_account = create_or_update_avito_account(code=code)
            item_list = get_items_list(avito_account)
            # TODO проверить  адекватность отработки когда больше 100 записей
            # TODO написать слой, котоырй будет записывать все объявления в БД
            return JsonResponse({"message": "Hello, you will redirect"})
        else:
            return JsonResponse({"message": "Please provide a code"}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class Test(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse({"message": "Please provide a code"}, status=400)
