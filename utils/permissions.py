from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from base import settings


class InnerAPIKey(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        api_key = request.META.get("Api-Key")

        if api_key is None:
            return False

        if api_key == settings.DJANGO_INNER_API_KEY:
            return True

        return False
