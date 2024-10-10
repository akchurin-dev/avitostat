import json
import yookassa
from django.contrib.auth.models import User
from payments.models import UserProfile
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from base import settings
from django.views.generic import TemplateView
from payments.models import Payment
from dateutil.parser import parse


class PaymentView(TemplateView):
    template_name = 'payment.html'  # Путь к вашему шаблону payment.html

    def get(self, request, *args, **kwargs):
        user_id = request.user.id
        # Формируем контекст с ID пользователя
        context = {
            'current_user_id': user_id
        }
        # Рендерим шаблон с переданным контекстом
        return render(request, self.template_name, context)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(View):
    def update_payment(self, object: dict):
        payment = Payment.objects.get(uuid=object.get("id"))

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
        user_profile = UserProfile.objects.get_or_create(user_id=payment.user.id)[0]
        user_profile.balance += float(object.get("income_amount").get("value"))
        user_profile.save()

    def post(self, request):
        # Декодируем байтовую строку в обычную строку
        decoded_data = request.body.decode('utf-8')
        object = json.loads(decoded_data).get("object")
        self.update_payment(object)
        self.update_balance(request, object)

        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name='dispatch')
class PaymentCreateView(View):
    def get(request, *args, **kwargs):
        # Логика создания платежа
        yookassa.Configuration.account_id = settings.YOOKASSA_TEST_SHOP_ID
        yookassa.Configuration.secret_key = settings.YOOKASSA_TEST_SECRET_KEY
        user = User.objects.filter(id=args[0].user.id).last()

        period = int(kwargs.get('period'))
        if period == 1:
            amount = 2000
            description = "1 месяц по 2000 рублей"
        if period == 3:
            amount = 5400
            description = "3 месяца по 1800 рублей"
        if period == 6:
            amount = 9000
            description = "6 месяцев по 1500 рублей"



        payment = Payment.objects.create(
            user_id=user.id,
            amount=amount,
        )

        payment_response = yookassa.Payment.create(
            {
                "amount": {
                    "value": amount,
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "http://127.0.0.1:8000.ru/admin"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    'orderNumber': payment.id
                },
            }
        )

        if payment_response:
            payment.uuid = payment_response.id
            payment.status = payment_response.status
            payment.confirmation_url = payment_response['confirmation']['confirmation_url']
            payment.save()

            return HttpResponseRedirect(payment_response['confirmation']['confirmation_url'])

        else:
            return JsonResponse(status=401, data={"Cant get payment response"})

