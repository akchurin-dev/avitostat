import json

import var_dump
import yookassa
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse
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

        # Преобразуем строку JSON в словарь
        data = json.loads(decoded_data)
        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name='dispatch')
class PaymentCreateView(View):
    def get(request, *args, **kwargs):
        # Логика создания платежа
        yookassa.Configuration.account_id = settings.YOOKASSA_TEST_SHOP_ID
        yookassa.Configuration.secret_key = settings.YOOKASSA_TEST_SECRET_KEY

        amount = 1
        order_id = Payment.objects.last().id + 1
        user = User.objects.filter(id=args[0].user.id).last()

        payment_response = yookassa.Payment.create(
            {
                "amount": {
                    "value": amount,
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "http://127.0.0.1:8000/admin"
                },
                "capture": True,
                "description": f"Заказ №{order_id} для {user.first_name}",
                "metadata": {
                    'orderNumber': order_id,
                },
            }
        )

        payment_response = var_dump.var_dump(payment_response)



        # Сохранение информации о платеже в базу
        Payment.objects.create(
            user_id=user.id,
            amount=amount,
            status=payment_response['status'],
            confirmation_url=payment_response['confirmation']['confirmation_url']
        )

        return HttpResponseRedirect(payment_response['confirmation']['confirmation_url'])

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
