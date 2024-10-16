import json

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from avito_account.oauth_utils import create_or_update_avito_account


@method_decorator(csrf_exempt, name='dispatch')
class CallbackView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get("code", None)
        state = request.GET.get("state", None)
        if state is not None:
            state_dict = json.loads(state)
            created_by_id = state_dict.get("created_by_id", None)
            if code:
                create_or_update_avito_account(code=code, created_by_id=int(created_by_id))
                # items_to_db(avito_account) # надо сделать всё асинхронно если есть в записи айтемов необходимость
                return JsonResponse({"message": "Hello, you will redirect"})
            else:
                return JsonResponse({"message": "Please provide a code"}, status=400)

