from django.contrib import admin
from django.urls import include
from django.urls import path


urlpatterns = [
    path('admin/', admin.site.urls),
    path("oauth/", include("avito_account.urls")),
    path("conversion/", include("conversion.urls")),
    path("messaging/", include("messaging.urls")),
]
