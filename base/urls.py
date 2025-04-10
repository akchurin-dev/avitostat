from django.contrib import admin
from django.urls import include
from django.urls import path

from base import settings


def trigger_error(request):
    raise Exception()


from django.http import HttpRequest
from django.shortcuts import redirect

def redirect_to_avito_oauth(request: HttpRequest, *args, **kwargs):
    params = "&".join([f"{k}={v}" for k, v in request.GET.items()])
    return redirect(f"/oauth/callback/?{params}")


urlpatterns = [
    path(r'jet/', include('jet.urls', 'jet')),  # Django JET URLS
    path('admin/', admin.site.urls),
    path("oauth/", include("avito_account.urls")),
    path("messaging/", include("messaging.urls")),
    path("deep_tests/", include("deep_tests.urls")),
    path('sentry-debug/', trigger_error),
    path('payments/', include('payments.urls')),
    path('chat_bot/', include('chat_bot.urls')),
    path('amo/', include('amo.urls')),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls
    urlpatterns += debug_toolbar_urls()

    urlpatterns.append(path('', redirect_to_avito_oauth))
