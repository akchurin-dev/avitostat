from django.urls import path
from .views import CallbackView, terms_of_service, trigger_error, CeleryTaskSentryTestView

urlpatterns = [
    path('sentry-debug/', trigger_error),
    path('sentry-debug-celery/', CeleryTaskSentryTestView.as_view()),
    path('callback/', CallbackView.as_view(), name='callback'),
    path('terms-of-service/', terms_of_service, name='terms_of_service'),  # Пользовательское соглашение
]
