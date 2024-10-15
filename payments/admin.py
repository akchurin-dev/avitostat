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
    pass


class UserProfileAdmin(SuperModelAdmin):
    pass


# Register your models here.
admin.site.register(Payment, PaymentAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
