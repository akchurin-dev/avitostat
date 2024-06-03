from django.contrib import admin
from django.urls import include
from django.urls import path


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path('admin/', admin.site.urls),
    path("oauth/", include("avito_account.urls")),
    path("conversion/", include("conversion.urls")),
    path("messaging/", include("messaging.urls")),
    path('sentry-debug/', trigger_error),
]
