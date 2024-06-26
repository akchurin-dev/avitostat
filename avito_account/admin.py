from django.contrib import admin
from django.contrib.admin import site
from django.db.models import Q

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
    exclude = ('access_token', 'refresh_token')

    def get_queryset(self, request):
        if request.user.is_superuser:
            queryset = super().get_queryset(request)
        else:
            queryset = super().get_queryset(request).filter(Q(company_id=request.user.pk) | Q(company_id=None))
        return queryset

    def has_add_permission(self, request):
        return False


site.register(AvitoAccount, AvitoAccountAdmin)
# site.register(Item, ItemAdmin)
# site.register(ServiceType)
# site.register(Operation)
