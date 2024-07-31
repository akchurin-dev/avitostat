from asgiref.sync import async_to_sync
from django.contrib import admin
from django.contrib.admin import site
from django.db.models import Q
from avito_account.models import AvitoAccount, AnalyticSchema, Criterion
import logging
from messaging.tasks import bad_messaging_week_report_async

logger = logging.getLogger(__name__)


class CriterionInline(admin.TabularInline):
    model = Criterion
    extra = 0


class AnalyticSchemaAdmin(admin.ModelAdmin):
    inlines = [CriterionInline, ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(created_by=request.user)


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

    actions = ['run_weekly_report']

    def run_weekly_report(self, request, queryset):
        object_ids = list(queryset.values_list('id', flat=True))

        try:
            async_to_sync(bad_messaging_week_report_async)(only_for_users=object_ids)
            self.message_user(request, "Отчет успешно сгенерирован и отправлен.", level='success')
        except Exception as e:
            logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
            self.message_user(request, f"Отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')

    run_weekly_report.short_description = "Отправить недельный отчет анализа переписок"


site.register(AvitoAccount, AvitoAccountAdmin)
site.register(AnalyticSchema, AnalyticSchemaAdmin)
