from django.urls import path
from .views import CallbackView, AvitoAccountListView, AvitoIdsListByTelegramView

urlpatterns = [
    path('callback/', CallbackView.as_view(), name='callback'),
    path('avito_accounts_list/', AvitoAccountListView.as_view(), name='avito_accounts_list'),
    path('avito_ids_list/<str:telegram_id>/', AvitoIdsListByTelegramView.as_view(), name='avito_accounts_list'),
]


