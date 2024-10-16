import json

from dateutil.parser import parse
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from payments.models import Payment, UserProfile


@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(View):
    def update_payment(self, object: dict):
        try:
            payment = Payment.objects.get(uuid=object.get("id"))
        except ObjectDoesNotExist:
            return
        # Обновление полей платежа с проверкой на наличие значений
        payment.status = object.get("status", payment.status)  # Оставляем текущее значение, если нет нового
        payment.currency = object.get("amount", {}).get("currency", payment.currency)
        payment.amount = float(object.get("amount", {}).get("value", payment.amount))
        payment.income_amount = float(object.get("income_amount", {}).get("value", payment.income_amount))

        payment.payment_method = object.get("payment_method", {}).get("type", payment.payment_method)

        payment.created_at = parse(object.get("created_at", payment.created_at))  # Дата создания платежа
        payment.updated_at = parse(object.get("captured_at", payment.updated_at))  # Дата списания платежа

        payment.test = bool(object.get("test", payment.test))  # Оставляем текущее значение, если нет нового
        payment.paid = bool(object.get("paid", payment.paid))  # Оставляем текущее значение, если нет нового

        # Установка URL подтверждения, если он присутствует
        if "confirmation_url" in object:
            payment.confirmation_url = object.get("confirmation_url")

        payment.description = object.get("description",
                                         payment.description)  # Оставляем текущее значение, если нет нового

        payment.save()

    def update_balance(self, request, object: dict):
        payment = Payment.objects.get(uuid=object.get("id"))
        user_profile = UserProfile.objects.get_or_create(user_id=payment.created_by.id)[0]
        user_profile.balance += payment.balance_tokens
        user_profile.save()

    def post(self, request):
        # Декодируем байтовую строку в обычную строку
        decoded_data = request.body.decode('utf-8')
        object = json.loads(decoded_data).get("object")
        self.update_payment(object)
        self.update_balance(request, object)

        return HttpResponse(status=200)
