from django.contrib import admin
from django.contrib.admin import site
from avito_account.models import AvitoAccount, Item
from conversion.models import ServiceType, Operation


class OperationInline(admin.TabularInline):
    model = Operation
    extra = 0


class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'status', 'address', 'category', 'url')
    list_filter = ('avito_account', 'status')
    inlines = [OperationInline, ]


site.register(AvitoAccount)
site.register(Item, ItemAdmin)
site.register(ServiceType)
site.register(Operation)
