import yookassa
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from avito_account.models.models import AvitoAccount
from base import settings
from payments.models import Payment


class PRICE:
    RATE_FREELANCER = 'freelancer'
    RATE_BUSINESS = 'business'
    RATE_STUDIO = 'studio'
    RATE_AGENCY = 'agency'

    PRICES = {
        'freelancer': 2000,
        'business': 1950,
        'studio': 1900,
        'agency': 1850,
    }

    @classmethod
    def get_price(cls, rate):
        return cls.PRICES.get(rate)

    @staticmethod
    def get_rate(active_accounts: int):
        if 0 < active_accounts <= 10:
            return PRICE.RATE_FREELANCER
        elif 11 <= active_accounts <= 20:
            return PRICE.RATE_BUSINESS
        elif 21 <= active_accounts <= 40:
            return PRICE.RATE_STUDIO
        elif active_accounts >= 41:
            return PRICE.RATE_AGENCY

    @staticmethod
    def get_discount(months_count: int):
        if 0 < months_count < 3:
            return 1
        elif 3 <= months_count <= 6:
            return 0.97
        if 6 <= months_count:
            return 0.95


@method_decorator(csrf_exempt, name='dispatch')
class PaymentCreateView(View):
    def get(request, *args, **kwargs):
        yookassa.Configuration.account_id = settings.YOOKASSA_TEST_SHOP_ID
        yookassa.Configuration.secret_key = settings.YOOKASSA_TEST_SECRET_KEY

        user = User.objects.filter(id=args[0].user.id).last()
        active_accounts = AvitoAccount.objects.filter(created_by=user).count()
        months_count = int(kwargs.get('months'))

        if settings.ENVIRONMENT == "DEVELOPMENT":  # TODO change script filling test DB and remove this code
            active_accounts = 5

        rate = PRICE.get_rate(active_accounts=active_accounts)
        price = PRICE.get_price(rate=rate)
        discount = PRICE.get_discount(months_count=months_count)
        discount_percents = int((1 - discount) * 100)
        balance_tokens = 2000 * active_accounts * months_count

        amount = price * active_accounts * months_count * discount
        description = (f"Тариф: {rate} - Цена: {price} р ///"
                       f"Аккаунтов к оплате: {active_accounts} ///"
                       f"Скидка: {discount_percents}% при оплате за {months_count} месяц(а) ///"
                       f"Итого к оплате: {amount} р")

        payment = Payment.objects.create(
            created_by=user,
            amount=amount,
            balance_tokens=balance_tokens,
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
