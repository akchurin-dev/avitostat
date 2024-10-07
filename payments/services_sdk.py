import yookassa
import var_dump as var_dump

from base import settings

yookassa.Configuration.account_id = settings.YOOKASSA_TEST_SHOP_ID
yookassa.Configuration.secret_key = settings.YOOKASSA_TEST_SECRET_KEY

res = yookassa.Payment.create(
    {
        "amount": {
            "value": 1,
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://avitostata.ru/admin"
        },
        "capture": True,
        "description": "Заказ №97",
        "metadata": {
            'orderNumber': '97'
        },
        "receipt": {
            "customer": {
                "full_name": "Ivanov Ivan Ivanovich123",
                "email": "email@email.ru",
                "phone": "79211234567",
                "inn": "6321341814"
            },
            # "items": [
            #     {
            #         "description": "Переносное зарядное устройство Хувей",
            #         "quantity": "1.00",
            #         "amount": {
            #             "value": 10,
            #             "currency": "RUB"
            #         },
            #         "vat_code": "2",
            #         "payment_mode": "full_payment",
            #         "payment_subject": "commodity",
            #         "country_of_origin_code": "CN",
            #         "product_code": "44 4D 01 00 21 FA 41 00 23 05 41 00 00",
            #         "customs_declaration_number": "10714040/140917/0090376",
            #         "excise": "2.00",
            #         "supplier": {
            #             "name": "string",
            #             "phone": "string",
            #             "inn": "string"
            #         }
            #     },
            # ]
        }
    }
)

var_dump.var_dump(res)
