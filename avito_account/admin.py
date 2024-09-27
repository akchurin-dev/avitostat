from django.contrib import admin
from django.db.models import Q
from avito_account.admin_panel.avito_account import AvitoAccountAdmin
from avito_account.admin_panel.sending_campaign import SendingCampaignAdmin, SendingReportAdmin
from avito_account.models.models import AvitoAccount, AnalyticSchema, Criterion, WorkSchedule, SendingCampaign, SendingReport
import logging


logger = logging.getLogger(__name__)


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
