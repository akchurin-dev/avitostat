from django.utils.deprecation import MiddlewareMixin
from .models import UserProfile


class UserProfileMiddleware(MiddlewareMixin):
    def process_template_response(self, request, response):
        if request.user.is_authenticated:
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            response.context_data = response.context_data or {}
            response.context_data['balance'] = user_profile.balance
        return response
