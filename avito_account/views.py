from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from avito_account.dao import items_to_db
from avito_account.oauth_utils import create_or_update_avito_account


@method_decorator(csrf_exempt, name='dispatch')
class CallbackView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", None)
        if code:
            avito_account = create_or_update_avito_account(code=code)
            # items_to_db(avito_account)
            return JsonResponse({"message": "Hello, you will redirect"})
        else:
            return JsonResponse({"message": "Please provide a code"}, status=400)
