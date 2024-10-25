from django.urls import path

from payments.views.create import PaymentCreateView, price_list_view
from payments.views.webhook import WebhookView

urlpatterns = [
    path('webhook/', WebhookView.as_view(), name='webhook'),
    path('create_payment/<int:months>/', PaymentCreateView.as_view(), name='create_payment'),
    path('price_list/', price_list_view, name='price_list'),
]
