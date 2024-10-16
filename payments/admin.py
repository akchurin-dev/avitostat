from django.contrib import admin

from payments.models import Payment, UserProfile


class SuperModelAdmin(admin.ModelAdmin):  # ТОЛЬКО ПРОСМОТР ДЛЯ НЕСУПЕРОВ
    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        else:
            return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        else:
            return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        else:
            return False


class PaymentAdmin(SuperModelAdmin):
    list_display = ('created_by', 'amount', 'balance_tokens', 'created_at', 'status')
    list_filter = ('status',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(paid=True, status=Payment.PAYMENT_STATUS_SUCCEEDED)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1
    fields = ['status', 'currency', 'amount', 'created_at']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(created_by=request.user)


class UserProfileAdmin(SuperModelAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(user=request.user)


# Register your models here.
admin.site.register(Payment, PaymentAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
