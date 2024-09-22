from django.contrib import admin
from django.forms import FloatField
from django.template.response import TemplateResponse
from avito_account.admin_panel.filters import ContragentFilter, TestFromProdFilter
from avito_account.models import AvitoAccount, SendingCampaign, SendingReport
from django.db.models import Sum, F, ExpressionWrapper, FloatField


class SendingReportInline(admin.TabularInline):
    model = SendingReport
    extra = 0
    readonly_fields = ['timestamp']

    def get_fields(self, request, obj=None):
        fields = ['avito_account', 'success', 'error_message', 'timestamp']
        if request.user.is_superuser:
            # Если пользователь суперпользователь, добавляем 'tokens_prompt' и 'tokens_completion'
            fields.extend(['tokens_prompt', 'tokens_completion'])
        return fields


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


class SendingReportAdmin(admin.ModelAdmin):
    list_filter = (ContragentFilter, TestFromProdFilter, 'avito_account', 'success', 'timestamp', )
    list_display = ['avito_account', 'tokens_completion', 'tokens_prompt', 'tokens_price', 'timestamp']

    def has_module_permission(self, request):
        return request.user.is_superuser

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Аннотация для вычисления стоимости токенов в базе данных
        queryset = qs.annotate(
            tokens_price=ExpressionWrapper(
                F('tokens_prompt') * 0.000125 + F('tokens_completion') * 0.0005,
                output_field=FloatField()
            )
        )

        return queryset.filter(
            campaign__sending_type=SendingCampaign.PDF,
            success=True
        )

    def tokens_price(self, obj):
        return round(obj.tokens_prompt * 0.000125 + obj.tokens_completion * 0.0005, 1)

    tokens_price.short_description = 'стоимость токенов'

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        # Убедимся, что response — это TemplateResponse
        if isinstance(response, TemplateResponse):
            # Получаем отфильтрованный queryset
            qs = response.context_data['cl'].queryset

            # Суммируем нужные поля и аннотированное поле
            total_tokens_completion = qs.aggregate(Sum('tokens_completion'))['tokens_completion__sum'] or 0
            total_tokens_prompt = qs.aggregate(Sum('tokens_prompt'))['tokens_prompt__sum'] or 0
            total_tokens_price = qs.aggregate(Sum('tokens_price'))['tokens_price__sum'] or 0

            # Передаем итоговые суммы в контекст
            response.context_data['total_tokens_completion'] = total_tokens_completion
            response.context_data['total_tokens_prompt'] = total_tokens_prompt
            response.context_data['total_tokens_price'] = round(total_tokens_price, 1)

        return response

