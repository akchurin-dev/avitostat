import json
import logging

from django import forms
from django.contrib import admin
from django.db.models import Q
from django.shortcuts import redirect

from avito_account.admin_panel.avito_account_actions import actualize_avito_items
from avito_account.admin_panel.avito_account_actions import actualize_avito_webhooks_subscriptions
from avito_account.admin_panel.avito_account_actions import celery_pdf_month_for_api_report
from avito_account.admin_panel.avito_account_actions import run_daily_pdf_report
from avito_account.admin_panel.avito_account_actions import run_pdf_all_report
from avito_account.admin_panel.avito_account_actions import run_pdf_all_test_from_prod_report
from avito_account.admin_panel.avito_account_actions import run_pdf_month_report
from avito_account.admin_panel.avito_account_actions import run_pdf_week_report
from avito_account.admin_panel.avito_account_actions import run_txt_all_report
from avito_account.admin_panel.avito_account_actions import run_txt_all_test_from_prod_report
from avito_account.admin_panel.avito_account_actions import run_txt_report
from avito_account.admin_panel.avito_account_actions import update_avito_accounts_tokens
from avito_account.models.models import AnalyticSchema
from avito_account.models.models import ExcludedItem
from avito_account.models.models import WorkSchedule
from base import settings
from chat_bot.models import CompanyBranch


logger = logging.getLogger(__name__)


class ExcludedItemForm(forms.ModelForm):
    class Meta:
        model = ExcludedItem
        fields = '__all__'
        widgets = {
            'id': forms.NumberInput(attrs={'style': 'width: 300px;'}),  # Установите нужную ширину
        }


class ExcludedItemInline(admin.TabularInline):
    model = ExcludedItem
    form = ExcludedItemForm
    extra = 5  # Количество пустых строк для добавления новых значений в админке
    verbose_name = "Объявление исключённое"
    verbose_name_plural = "Объявления исключённые "


class WorkScheduleInline(admin.StackedInline):
    model = WorkSchedule
    can_delete = False
    extra = 0


class CompanyBranchInline(admin.TabularInline):
    model = CompanyBranch
    readonly_fields = ["location_slug"]
    extra = 0


class AvitoAccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'telegram_id', 'phone', 'created_by')
    fields = [
        'name',
        'telegram_id',
        'phone',
        'profile_url',
        'analytic_schema',
        'id',
        'balance_alerting',
        'created_by',
        'weekly_text_report',
        'weekly_pdf_report',
    ]
    readonly_fields = ('id',)
    inlines = [WorkScheduleInline, ExcludedItemInline, CompanyBranchInline]
    actions = [
        actualize_avito_items,
        actualize_avito_webhooks_subscriptions,
        celery_pdf_month_for_api_report,
        run_daily_pdf_report,
        run_pdf_all_report,
        run_pdf_all_test_from_prod_report,
        run_pdf_month_report,
        run_pdf_week_report,
        run_txt_all_report,
        run_txt_all_test_from_prod_report,
        run_txt_report,
        update_avito_accounts_tokens,
    ]
    exclude = ('access_token', 'refresh_token')

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            # Удаляем только определенные экшены для не-суперадминов
            restricted_actions = ['celery_pdf_month_for_api_report',
                                  'run_txt_all_report',
                                  'run_pdf_all_report',
                                  'run_pdf_all_test_from_prod_report',
                                  'run_txt_all_test_from_prod_report']
            for action in restricted_actions:
                if action in actions:
                    del actions[action]
        return actions

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
            if request and not request.user.is_superuser:
                kwargs["queryset"] = AnalyticSchema.objects.filter(created_by=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def add_view(self, request, form_url="", extra_context=None):
        state = {
            "created_by_id": request.user.pk,
        }
        return redirect(f"https://www.avito.ru/oauth?response_type=code&client_id={settings.AVITO_CLIENT_ID}&scope=messenger"
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

    # def get_fieldsets(self, request, obj=None):
    #     fieldsets = [
    #         (None, {
    #             'fields': (
    #                 'name', 'telegram_id', 'phone',
    #                 'profile_url', 'analytic_schema', 'id', 'balance_alerting', 'created_by',
    #             ),
    #         }),
    #     ]
    #     return fieldsets
