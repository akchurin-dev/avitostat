from django.contrib import admin

from amo.models import AmocrmAccount




# class AmocrmAccountAdmin(admin.ModelAdmin):
#     def response_add(self, request, obj, post_url_continue=None):
#         """
#         Этот метод вызывается после добавления нового объекта.
#         Мы выполняем редирект на сторонний сервис только после добавления записи.
#         """
#         # Если не нажата кнопка "Добавить еще", выполняем редирект
#         if "_addanother" not in request.POST:
#             # Параметр "state" можно задать, если нужно передавать какие-то данные
#             state = {
#                 "created_by_id": request.user.id,
#             }
#             # Редирект на сторонний сервис (например, на OAuth)
#             return HttpResponseRedirect(
#                 f"https://www.amocrm.ru/oauth?client_id=5cc2f970-fe3d-47a0-9b38-86d531fa92ff&state={state}")
#
#         # Если была нажата кнопка "Добавить еще", возвращаемся на форму добавления нового объекта
#         return super().response_add(request, obj, post_url_continue)
#
#
# admin.site.register(AmocrmAccount, AmocrmAccountAdmin)
