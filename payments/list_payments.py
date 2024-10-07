from pprint import pprint

import yookassa
import var_dump as var_dump

from base import settings

yookassa.Configuration.account_id = settings.YOOKASSA_TEST_SHOP_ID
yookassa.Configuration.secret_key = settings.YOOKASSA_TEST_SECRET_KEY

res = yookassa.Payment.list()
for p in res:
    pprint(p)
