import json
import math
from django.contrib import admin
from django.db.models import Q, Sum, ExpressionWrapper
from django.forms import FloatField
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from avito_account.admin_panel.sending_campaign import SendingCampaignAdmin, SendingReportAdmin
from avito_account.models import AvitoAccount, AnalyticSchema, Criterion, WorkSchedule, SendingCampaign, SendingReport
import logging
from conversion.tasks import send_text_report_all_async_task
from messaging.tasks import bad_messaging_week_report_async_task
from django.db.models import Sum, F, ExpressionWrapper, FloatField
logger = logging.getLogger(__name__)


class WorkScheduleInline(admin.StackedInline):
    model = WorkSchedule
    can_delete = False
    extra = 0


class AvitoAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'telegram_id', 'phone')
    readonly_fields = ('id',)
    inlines = [WorkScheduleInline]

    exclude = ('access_token', 'refresh_token')

    def get_queryset(self, request):
        if request.user.is_superuser:
            queryset = super().get_queryset(request)
        else:
            queryset = super().get_queryset(request).filter(Q(created_by_id=request.user.pk))
        return queryset

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # Проверяем, есть ли уже связанный объект WorkSchedule, если нет - создаем
        if not hasattr(obj, 'work_schedules') or obj.work_schedules is None:
            WorkSchedule.objects.get_or_create(avito_account=obj)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):  #  Фильтрует выпадающие связанные списки
        if db_field.name == "analytic_schema":
            if not request.user.is_superuser:
                kwargs["queryset"] = AnalyticSchema.objects.filter(created_by=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def add_view(self, request, form_url="", extra_context=None):
        state = {
            "created_by_id": request.user.id,
        }
        return redirect("https://www.avito.ru/oauth?response_type=code&client_id=_pBlAY6LnBWr_sKlgHfX&scope=messenger"
                        ":read,messenger:write,user_balance:read,user_operations:read,user:read,autoload:reports,"
                        f"items:info,items:apply_vas,stats:read&state={json.dumps(state)}")

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
            bad_messaging_week_report_async_task(only_for_users=object_ids)
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
                    'name', 'telegram_id', 'phone',
                    'profile_url', 'analytic_schema', 'id', 'created_by',
                ),
            }),
        ]
        return fieldsets
