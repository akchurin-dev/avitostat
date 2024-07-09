from django.urls import path
from .views import CallbackView, AvitoAccountListView, AvitoAccountByTelegramIdView

urlpatterns = [
    path('callback/', CallbackView.as_view(), name='callback'),
    path('avito_accounts_list/', AvitoAccountListView.as_view(), name='avito_accounts_list'),
    path('avito_account_by_telegram_id/<str:telegram_id>/', AvitoAccountByTelegramIdView.as_view(), name='avito_account_by_telegram_id'),
]


