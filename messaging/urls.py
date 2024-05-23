from django.urls import path

from messaging.views import ChatListView

urlpatterns = [
    path('week_report/<str:telegram_id>/', ChatListView.as_view(), name='chat_list'),
]