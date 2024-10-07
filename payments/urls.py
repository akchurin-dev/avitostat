from django.urls import path
from .views import PaymentView, WebhookView, PaymentCreateView

urlpatterns = [
    path('payment/', PaymentView.as_view(), name='payment'),  # template of payment yookassa
    path('webhook/', WebhookView.as_view(), name='webhook'),
    path('create_payment/', PaymentCreateView.as_view(), name='create_payment'),
]
