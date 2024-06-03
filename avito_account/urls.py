from django.urls import path
from .views import CallbackView, AvitoAccountListView

urlpatterns = [
    path('callback/', CallbackView.as_view(), name='callback'),
    path('avito_accounts_list/', AvitoAccountListView.as_view(), name='avito_accounts_list'),
]
