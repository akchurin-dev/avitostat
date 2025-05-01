from django.urls import path

from amo import views


urlpatterns = [
    path("oauth", views.oauth_callback),
    path("webhook-inbox", views.webhook_inbox),
    path("sync-account/<int:pk>", views.syncronize_amo_account),
    path("update-prompt-example/<int:pk>", views.update_prompt_example),
]
