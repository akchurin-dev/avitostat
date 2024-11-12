import json
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from payments.models import Payment, UserProfile


@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(View):
    def post(self, request):
        # Декодируем байтовую строку в обычную строку
        decoded_data = request.body.decode('utf-8')
        object = json.loads(decoded_data).get("object")
        Payment.update_by_object(object=object)
        UserProfile.update_balance_by_object(object=object)

        return HttpResponse(status=200)
