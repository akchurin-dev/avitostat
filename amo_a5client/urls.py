from django.urls import path

import amo_a5client.views


urlpatterns = [
    path("message-contact-links", amo_a5client.views.ContactMessageLinksAPIView.as_view()),
]
