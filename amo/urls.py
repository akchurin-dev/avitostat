from django.urls import path

from amo.views import AmocrmOauthCallbackView

urlpatterns = [
    path('oauth_callback/', AmocrmOauthCallbackView.as_view(), name='oauth_callback'),
]
