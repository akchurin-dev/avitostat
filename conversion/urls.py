from django.urls import path

from conversion.views import Test

urlpatterns = [
    path('test/', Test.as_view(), name='test'),
]
