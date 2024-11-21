from django.urls import path
from .views import CallbackView, terms_of_service, TestBalanceView

urlpatterns = [
    path('callback/', CallbackView.as_view(), name='callback'),
    path('balance/', TestBalanceView.as_view(), name='balance'),
    path('terms-of-service/', terms_of_service, name='terms_of_service'),  # Пользовательское соглашение
]
