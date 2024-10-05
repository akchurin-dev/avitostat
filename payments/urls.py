from django.urls import path
from .views import create_payment, PaymentView

urlpatterns = [
    path('payment/', PaymentView.as_view(), name='payment'),  # template of payment yookassa
    path('create/', create_payment, name='create_payment'),
]
