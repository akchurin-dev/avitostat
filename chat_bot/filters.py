from django.contrib.admin import SimpleListFilter
from django.db.models import Q


class ChatIDFilter(SimpleListFilter):
    title = "Chat ID"
    parameter_name = "chat_id"

    def lookups(self, request, model_admin):
        # Получаем выбранный AvitoAccount из фильтров
        avito_account_id = request.GET.get("avito_account__id__exact", None)
        if avito_account_id is not None:
            # Получаем список уникальных chat_id, связанных с выбранным AvitoAccount
            return (
                model_admin.model.objects.filter(avito_account_id=avito_account_id)
                .values_list("chat_id", "chat_id")
                .distinct()
            )
        return []

    def queryset(self, request, queryset):
        # Применяем фильтр по выбранному chat_id
        if self.value():
            return queryset.filter(chat_id=self.value())
        return queryset


class ContactFilter(SimpleListFilter):
    title = "Контакты"
    parameter_name = "has_contact"

    def lookups(self, request, model_admin):
        return [
            ("yes", "Имеется контакт"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(
                Q(address__isnull=False) |
                Q(mobile__isnull=False) |
                Q(whatsapp__isnull=False) |
                Q(telegram__isnull=False) |
                Q(email__isnull=False,)
            )
        return queryset

