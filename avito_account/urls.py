from django.urls import path
from .views import CallbackView, Test

urlpatterns = [
    path('callback/', CallbackView.as_view(), name='callback'),
    path('test/', Test.as_view(), name='test'),
]
