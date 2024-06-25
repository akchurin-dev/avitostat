from django.contrib import admin
from django.contrib.admin import site

from avito_account.models import AvitoAccount
from conversion.models import Operation


class OperationInline(admin.TabularInline):
    model = Operation
    extra = 0


class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'status', 'address', 'category', 'url')
    list_filter = ('avito_account', 'status')
    inlines = [OperationInline, ]


class AvitoAccountAdmin(admin.ModelAdmin):
    list_display = ('company', 'name', 'telegram_id', 'phone', 'profile_url')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(company_id=request.user.pk)


site.register(AvitoAccount, AvitoAccountAdmin)
# site.register(Item, ItemAdmin)
# site.register(ServiceType)
# site.register(Operation)
