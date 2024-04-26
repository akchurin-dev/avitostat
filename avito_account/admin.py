from django.contrib.admin import site

# Register your models here.
from avito_account.models import AvitoAccount, Item, ServiceType, Operation

site.register(AvitoAccount)
site.register(Item)
site.register(ServiceType)
site.register(Operation)
