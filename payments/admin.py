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


class UserProfileInline(admin.TabularInline):
    model = UserProfile
    verbose_name_plural = 'Профиль пользователя'
    extra = 0
    can_delete = False
    can_create = False
    can_edit = False


class PaymentAdmin(SuperModelAdmin):
    list_display = ('created_by', 'amount', 'balance_tokens', 'created_at', 'status')
    list_filter = ('status',)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(paid=True, status=Payment.PAYMENT_STATUS_SUCCEEDED)


class UserProfileAdmin(SuperModelAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(user=request.user)


# Register your models here.
admin.site.register(Payment, PaymentAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
