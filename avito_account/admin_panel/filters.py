from django.contrib.admin import SimpleListFilter
from django.contrib.auth.models import User
from avito_account.models import AvitoAccount


class ContragentFilter(SimpleListFilter):
    title = 'Контрагент'
    parameter_name = 'avito_account_created_by'

    def lookups(self, request, model_admin):
        users = set(AvitoAccount.objects.values_list('created_by', flat=True))
        return [(user.id, user.username) for user in User.objects.filter(id__in=users)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(avito_account__created_by_id=self.value())
        return queryset


class TestFromProdFilter(SimpleListFilter):
    title = 'Для тестирования'
    parameter_name = 'test_from_prod'

    def lookups(self, request, model_admin):
        return [(True, 'Да'), (False, 'Нет')]

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(campaign__test_from_prod=self.value() == 'True')

        # Установить значение по умолчанию на 'Нет' (False)
        return queryset.filter(campaign__test_from_prod=False)
