from django.urls import path
from .views import create_payment, check_payment_status

urlpatterns = [
    path('create/', create_payment, name='create_payment'),
    path('status/<str:order_id>/', check_payment_status, name='check_payment_status'),
]
