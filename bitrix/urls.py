from django.urls import path

from bitrix import views as bitrix_views


urlpatterns = [
    path("installation-link", bitrix_views.get_installation_link),
    path("application-installed", bitrix_views.bitrix_app_installed),
    path("webhook-inbox", bitrix_views.bitrix_bot_event),
]
