from django.http import HttpResponseRedirect
from .services import YookassaService
from django.views.generic import TemplateView


class PaymentView(TemplateView):
    template_name = 'payment.html'  # Путь к вашему шаблону payment.html


def create_payment(request):
    # Логика создания платежа
    order_id = 'example_order_id'
    amount = 100.00
    currency = 'RUB'
    description = 'Оплата услуг'
    return_url = 'https://example.com/success'

    yookassa = YookassaService()
    payment_response = yookassa.create_payment(amount, currency, description, order_id, return_url)
    print(123)

    # Сохранение информации о платеже в базу
    # Payment.objects.create(
    #     order_id=order_id,
    #     amount=amount,
    #     status=payment_response['status'],
    #     confirmation_url=payment_response['confirmation']['confirmation_url']
    # )

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
