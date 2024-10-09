import json
from datetime import timezone

import var_dump
import yookassa
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from base import settings
from django.views.generic import TemplateView

from payments.models import Payment


class PaymentView(TemplateView):
    template_name = 'payment.html'  # Путь к вашему шаблону payment.html

    def get(self, request, *args, **kwargs):
        # Получаем ID текущего пользователя
        user_id = request.user.id
        # Формируем контекст с ID пользователя
        context = {
            'current_user_id': user_id
        }
        # Рендерим шаблон с переданным контекстом
        return render(request, self.template_name, context)


@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(View):
    def post(self, request):
        # Декодируем байтовую строку в обычную строку
        decoded_data = request.body.decode('utf-8')
        object = json.loads(decoded_data).get("object")

        payment = Payment.objects.get(uuid=object.get("id"))
        payment.status = object.get("status")
        payment.currency = object.get("amount").get("currency")
        payment.amount = float(object.get("amount").get("value"))
        payment.income_amount = float(object.get("income_amount").get("value"))

        payment.payment_method = object.get("payment_method").get("type")
        # payment.created_at = timezone.now()
        # payment.updated_at = timezone.now()

        payment.test = bool(object.get("test"))
        payment.paid = bool(object.get("paid"))
        payment.confirmation_url = object.get("confirmation_url")
        payment.description = object.get("description")
        payment.save()

        return HttpResponse(status=200)

        # {'event': 'payment.succeeded',
        #  'object': {'amount': {'currency': 'RUB', 'value': '1.00'},
        #             'authorization_details': {'auth_code': '143906',
        #                                       'rrn': '320912593370888',
        #                                       'three_d_secure': {'applied': False,
        #                                                          'challenge_completed': False,
        #                                                          'method_completed': False}},
        #             'captured_at': '2024-10-09T07:58:02.429Z',
        #             'created_at': '2024-10-09T07:57:53.634Z',
        #             'description': '44',
        #             'id': '2e984b41-000f-5000-a000-1a08957a5e35',
        #             'income_amount': {'currency': 'RUB', 'value': '0.96'},
        #             'metadata': {'cms_name': 'yookassa_sdk_python',
        #                          'orderNumber': '44'},
        #             'paid': True,
        #             'payment_method': {'card': {'card_product': {'code': 'E'},
        #                                         'card_type': 'MasterCard',
        #                                         'expiry_month': '11',
        #                                         'expiry_year': '2011',
        #                                         'first6': '555555',
        #                                         'issuer_country': 'US',
        #                                         'last4': '4444'},
        #                                'id': '2e984b41-000f-5000-a000-1a08957a5e35',
        #                                'saved': False,
        #                                'title': 'Bank card *4444',
        #                                'type': 'bank_card'},
        #             'recipient': {'account_id': '469140', 'gateway_id': '2324047'},
        #             'refundable': True,
        #             'refunded_amount': {'currency': 'RUB', 'value': '0.00'},
        #             'status': 'succeeded',
        #             'test': True},
        #  'type': 'notification'}


@method_decorator(csrf_exempt, name='dispatch')
class PaymentCreateView(View):
    def get(request, *args, **kwargs):
        # Логика создания платежа
        yookassa.Configuration.account_id = settings.YOOKASSA_TEST_SHOP_ID
        yookassa.Configuration.secret_key = settings.YOOKASSA_TEST_SECRET_KEY

        user = User.objects.filter(id=args[0].user.id).last()
        amount = 1000
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
                "description": f"Заказ №{payment.id}",
                "metadata": {
                    'orderNumber': payment.id
                },
                "receipt": {
                    "customer": {
                        "email": "email@email.ru",
                    },
                }
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

# def check_payment_status(request, order_id):
#     payment = get_object_or_404(Payment, order_id=order_id)
#     yookassa = YookassaService()
#     status_response = yookassa.get_payment_status(payment.order_id)
#
#     # Обновление статуса в базе данных
#     payment.status = status_response['status']
#     payment.save()
#
#     return JsonResponse({'status': payment.status})
