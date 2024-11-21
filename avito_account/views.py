import json

from asgiref.sync import sync_to_async
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from avito_account.api.get_balance import get_balance
from avito_account.models.models import AvitoAccount
from avito_account.oauth_utils import create_or_update_avito_account
from django.shortcuts import render, redirect

from base import settings


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
                if settings.ENVIRONMENT == "PRODUCTION":
                    redirect_url = "https://avitostata.ru/admin/avito_account/avitoaccount/"
                    return HttpResponseRedirect(redirect_url)
                else:
                    return JsonResponse(
                        {"message": "Аккаунт успешно добавлен, вы будете перенаправлены на главную страницу"})
            else:
                return JsonResponse({"message": "Предоставьте код авторизации"}, status=400)


def terms_of_service(request):
    return render(request, 'terms_of_service.html')


@method_decorator(csrf_exempt, name='dispatch')
class TestBalanceView(View):
    async def get(self, request, *args, **kwargs):
        avito_account = await sync_to_async(list)(AvitoAccount.objects.filter(id=145213826))
        await get_balance(avito_account[0])
