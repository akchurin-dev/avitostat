from django.utils.deprecation import MiddlewareMixin

from avito_account.models.models import AvitoAccount
from base import settings
from .models import UserProfile


class UserProfileMiddleware(MiddlewareMixin):
    def process_template_response(self, request, response):
        if request.user.is_authenticated:
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            response.context_data = response.context_data or {}
            response.context_data['balance'] = user_profile.balance
            response.context_data['days_left'] = int(user_profile.balance // 480) * 7
            response.context_data['active_accounts'] = AvitoAccount.objects.filter(created_by=request.user).count()
            if settings.ENVIRONMENT == "DEVELOPMENT":  # TODO change script filling test DB and remove this code
                response.context_data['active_accounts'] = 5
        return response
