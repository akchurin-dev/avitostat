from django.contrib import admin
from django.urls import include
from django.urls import path


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns = [
    path(r'jet/', include('jet.urls', 'jet')),  # Django JET URLS
    path('admin/', admin.site.urls),
    path("oauth/", include("avito_account.urls")),
    path("messaging/", include("messaging.urls")),
    path("deep_tests/", include("deep_tests.urls")),
    path('sentry-debug/', trigger_error),
    path('payments/', include('payments.urls')),
    path('chat_bot/', include('chat_bot.urls')),
    path('bitrix/', include("bitrix.urls")),
]
