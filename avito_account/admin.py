from django.contrib import admin
from django.contrib.admin import site

# Register your models here.
from avito_account.models import AvitoAccount, Item, ServiceType, Operation


class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'status', 'address', 'category', 'url')
    list_filter = ('avito_account', 'status', 'address')


site.register(AvitoAccount)
site.register(Item, ItemAdmin)
site.register(ServiceType)
site.register(Operation)
