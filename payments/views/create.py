import yookassa
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from avito_account.models.models import AvitoAccount
from base import settings
from payments.models import Payment


@method_decorator(csrf_exempt, name='dispatch')
class PaymentCreateView(View):
    def get(request, *args, **kwargs):
        # Логика создания платежа
        yookassa.Configuration.account_id = settings.YOOKASSA_TEST_SHOP_ID
        yookassa.Configuration.secret_key = settings.YOOKASSA_TEST_SECRET_KEY
        user = User.objects.filter(id=args[0].user.id).last()
        active_accounts = AvitoAccount.objects.filter(created_by=user).count()

        if settings.ENVIRONMENT == "DEVELOPMENT":   # TODO change script filling test DB and remove this code
            active_accounts = 5

        rate = int(kwargs.get('rate'))
        if rate == 1:
            amount = 2000 * active_accounts
            description = f"Тариф 'Фрилансер' 2000р для {active_accounts} аккаунтов = {amount} рублей"
        if rate == 2:
            amount = 1950 * active_accounts
            description = f"Тариф 'Фрилансер' 1950р для {active_accounts} аккаунтов = {amount} рублей"
        if rate == 3:
            amount = 1900 * active_accounts
            description = f"Тариф 'Фрилансер' 1900р для {active_accounts} аккаунтов = {amount} рублей"


        payment = Payment.objects.create(
            amount=amount,
            created_by=user
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
