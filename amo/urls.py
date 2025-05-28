from django.urls import path

from amo import views


urlpatterns = [
    path("oauth", views.oauth_callback),
    path("application-disabled", views.application_disabled_callback),
    path("webhook", views.amo_webhook),
    path("sync-account/<int:pk>", views.syncronize_amo_account),
]
