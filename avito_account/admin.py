from django.contrib.admin import site

# Register your models here.
from avito_account.models import AvitoAccount

site.register(AvitoAccount)
