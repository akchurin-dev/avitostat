from django.contrib import admin
from django.contrib.admin import site
from django.db.models import Q
from django.template.response import TemplateResponse
from django.urls import path

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
    readonly_fields = ('id',)

    # exclude = ('access_token', 'refresh_token')

    def get_queryset(self, request):
        if request.user.is_superuser:
            queryset = super().get_queryset(request)
        else:
            queryset = super().get_queryset(request).filter(Q(company_id=request.user.pk) | Q(company_id=None))
        return queryset

    def has_add_permission(self, request):
        return False

    def get_fields(self, request, obj=None):  # Only for view id in details and hide in list
        fields = super().get_fields(request, obj)
        if obj is not None and 'id' not in fields:
            fields = ['id'] + list(fields)
        return fields

    def get_readonly_fields(self, request, obj=None):  # Only for view id in details and hide in list
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is not None and 'id' not in readonly_fields:
            readonly_fields = ['id'] + list(readonly_fields)
        return readonly_fields

    change_form_template = "admin/avito_account_change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:object_id>/print_id/',
                self.admin_site.admin_view(self.print_instance_id),
                name='print_instance_id',
            ),
        ]
        return custom_urls + urls

    def print_instance_id(self, request, object_id):
        # Ваша логика здесь (например, просто напечатаем в консоль)
        print(f"Instance ID: {object_id}")
        self.message_user(request, f"Instance ID: {object_id} has been printed in the console.")
        return TemplateResponse(request, "admin/instance_id_printed.html", {})


site.register(AvitoAccount, AvitoAccountAdmin)
# site.register(Item, ItemAdmin)
# site.register(ServiceType)
# site.register(Operation)
