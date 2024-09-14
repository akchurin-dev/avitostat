from django.contrib import admin
from django.contrib.admin import site
from django.db.models import Q
from avito_account.models import AvitoAccount, AnalyticSchema, Criterion, WorkSchedule, SendingCampaign, SendingReport
import logging

from conversion.tasks import send_text_report_all_async_task
from messaging.tasks import bad_messaging_week_report_async_task

logger = logging.getLogger(__name__)


class CriterionInline(admin.TabularInline):
    model = Criterion
    extra = 0


class WorkScheduleInline(admin.StackedInline):
    model = WorkSchedule
    can_delete = False
    extra = 0


class AnalyticSchemaAdmin(admin.ModelAdmin):
    inlines = [CriterionInline, ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(created_by=request.user)


class AvitoAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'telegram_id', 'phone')
    readonly_fields = ('id',)
    inlines = [WorkScheduleInline]

    exclude = ('access_token', 'refresh_token')

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

    actions = ['run_pdf_report', 'run_pdf_all_report', 'run_txt_report', 'run_txt_all_report']

    def run_pdf_report(self, request, queryset):
        object_ids = list(queryset.values_list('id', flat=True))

        try:
            bad_messaging_week_report_async_task.delay(only_for_users=object_ids)
            self.message_user(request, "ПДФ отчет успешно сгенерирован и отправлен.", level='success')
        except Exception as e:
            logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
            self.message_user(request, f"ПДФ отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')

    run_pdf_report.short_description = "ПДФ отчет отправить"

    def run_pdf_all_report(self, request, queryset):
        try:
            bad_messaging_week_report_async_task.delay()
            self.message_user(request, "ПДФ ВСЕМ отчет успешно сгенерирован и отправлен.", level='success')
        except Exception as e:
            logger.error(f"Ошибка при отправке отчета: {e}", exc_info=True)
            self.message_user(request, f"ПДФ ВСЕМ отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')

    run_pdf_all_report.short_description = "ПДФ ВСЕМ отчет отправить"

    def run_txt_report(self, request, queryset):
        avito_account_ids = list(queryset.values_list('id', flat=True))
        try:
            send_text_report_all_async_task.delay(only_for_users=avito_account_ids)
            self.message_user(request, "ТЕКСТОВЫЙ отчет успешно сгенерирован и отправлен.", level='success')
        except Exception as e:
            logger.error(f"ТЕКСТОВЫЙ ошибка при отправке отчета: {e}", exc_info=True)
            self.message_user(request, f"Отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')

    run_txt_report.short_description = "ТЕКСТОВЫЙ отчет отправить"

    def run_txt_all_report(self, request, queryset):
        try:
            send_text_report_all_async_task.delay()
            self.message_user(request, "ТЕКСТОВЫЙ ВСЕМ отчет успешно сгенерирован и отправлен.", level='success')
        except Exception as e:
            logger.error(f"ТЕКСТОВЫЙ ВСЕМ ошибка при отправке отчета: {e}", exc_info=True)
            self.message_user(request, f"Отчет не удалось отправить" f" Ошибка сервера - {e}", level='error')

    run_txt_all_report.short_description = "ТЕКСТОВЫЙ ВСЕМ отчет отправить"

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            (None, {
                'fields': (
                    'company', 'name', 'telegram_id', 'phone',
                    'profile_url', 'analytic_schema', 'id',
                ),
            }),
        ]
        return fieldsets


class SendingReportInline(admin.TabularInline):
    model = SendingReport
    extra = 0  # Количество дополнительных пустых форм для создания новых объектов
    fields = ['avito_account', 'success', 'error_message', 'pdf_path', 'timestamp']
    readonly_fields = ['timestamp']


class SendingCampaignAdmin(admin.ModelAdmin):
    inlines = [SendingReportInline]
    list_display = ['sending_type', 'created_at', 'name', ]
    list_filter = ['sending_type', 'test_from_prod', 'created_at']
    search_fields = ['name']


# admin.site.register(WorkSchedule)   # TODO if you need it - only for superuser open it
site.register(AvitoAccount, AvitoAccountAdmin)
site.register(AnalyticSchema, AnalyticSchemaAdmin)
admin.site.register(SendingCampaign, SendingCampaignAdmin)
