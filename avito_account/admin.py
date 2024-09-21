import json

import math
from django.contrib import admin
from django.db.models import Q, Sum, ExpressionWrapper
from django.forms import FloatField
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from avito_account.models import AvitoAccount, AnalyticSchema, Criterion, WorkSchedule, SendingCampaign, SendingReport
import logging
from conversion.tasks import send_text_report_all_async_task
from messaging.tasks import bad_messaging_week_report_async_task

logger = logging.getLogger(__name__)


class WorkScheduleInline(admin.StackedInline):
    model = WorkSchedule
    can_delete = False
    extra = 0


class CriterionInline(admin.TabularInline):
    model = Criterion
    extra = 0
    exclude = ('created_by',)

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


class AnalyticSchemaAdmin(admin.ModelAdmin):
    inlines = [CriterionInline, ]
    exclude = ('created_by',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(created_by=request.user)

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user
        super().save_model(request, obj, form, change)


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


class SendingReportInline(admin.TabularInline):
    model = SendingReport
    extra = 0  # Количество дополнительных пустых форм для создания новых объектов
    fields = ['avito_account', 'success', 'error_message', 'timestamp', 'tokens_prompt', 'tokens_completion']
    readonly_fields = ['timestamp']


class SendingCampaignAdmin(admin.ModelAdmin):
    inlines = [SendingReportInline]
    list_display = ['sending_type', 'created_at', 'test_from_prod', 'name', ]
    list_filter = ['accounts_presented', 'sending_type', 'test_from_prod', 'created_at']
    search_fields = ['name']

    def get_queryset(self, request):
        # Получаем исходный queryset
        queryset = super().get_queryset(request)

        # Если пользователь суперпользователь, то показываем все записи
        if request.user.is_superuser:
            return queryset

        # Получаем все аккаунты, созданные текущим пользователем
        user_created_accounts = AvitoAccount.objects.filter(created_by=request.user)

        # Фильтруем рассылки, в которых в поле `accounts_presented` есть аккаунты, созданные этим пользователем
        return queryset.filter(accounts_presented__in=user_created_accounts).distinct()

from django.db.models import Sum, F, ExpressionWrapper, FloatField
class SendingReportAdmin(admin.ModelAdmin):
    list_filter = ('avito_account', 'campaign', 'success', 'error_message', 'pdf_path', 'timestamp')
    list_display = ['avito_account', 'tokens_completion', 'tokens_prompt', 'tokens_price', 'timestamp']

    def has_module_permission(self, request):
        return request.user.is_superuser

    # def get_queryset(self, request):
    #     return super().get_queryset(request).filter(
    #         campaign__sending_type=SendingCampaign.PDF,
    #         campaign__test_from_prod=False,
    #         success=True
    #     )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Аннотация для вычисления стоимости токенов в базе данных
        return qs.annotate(
            tokens_price=ExpressionWrapper(
                F('tokens_prompt') * 0.000125 + F('tokens_completion') * 0.0005,
                output_field=FloatField()
            )
        )

    def tokens_price(self, obj):
        # Здесь добавьте логику для вычисления значения
        return round(obj.tokens_prompt * 0.000125 + obj.tokens_completion * 0.0005, 1)  # Например, это просто возвращает значение поля success

    tokens_price.short_description = 'стоимость токенов'

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        # Убедимся, что response — это TemplateResponse
        if isinstance(response, TemplateResponse):
            # Получаем queryset
            qs = self.get_queryset(request)

            # Суммируем нужные поля и аннотированное поле
            total_tokens_completion = qs.aggregate(Sum('tokens_completion'))['tokens_completion__sum'] or 0
            total_tokens_prompt = qs.aggregate(Sum('tokens_prompt'))['tokens_prompt__sum'] or 0
            total_tokens_price = qs.aggregate(Sum('tokens_price'))['tokens_price__sum'] or 0

            # Передаем итоговые суммы в контекст
            response.context_data['total_tokens_completion'] = total_tokens_completion
            response.context_data['total_tokens_prompt'] = total_tokens_prompt
            response.context_data['total_tokens_price'] = round(total_tokens_price, 1)

        return response


class WorkScheduleAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser

    def get_queryset(self, request):
        if request.user.is_superuser:
            queryset = super().get_queryset(request)
        else:
            queryset = super().get_queryset(request).filter(Q(avito_account__created_by_id=request.user.pk))
        return queryset


admin.site.register(WorkSchedule, WorkScheduleAdmin)
admin.site.register(AvitoAccount, AvitoAccountAdmin)
admin.site.register(AnalyticSchema, AnalyticSchemaAdmin)
admin.site.register(SendingCampaign, SendingCampaignAdmin)
admin.site.register(SendingReport, SendingReportAdmin)
