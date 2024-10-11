from django.urls import path

from payments.views.create import PaymentCreateView
from payments.views.payment import PaymentView
from payments.views.webhook import WebhookView

urlpatterns = [
    path('payment/', PaymentView.as_view(), name='payment'),  # template of payment yookassa
    path('webhook/', WebhookView.as_view(), name='webhook'),
    path('create_payment/<int:rate>/', PaymentCreateView.as_view(), name='create_payment'),
]
