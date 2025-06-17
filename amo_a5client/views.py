from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

import amo_a5client.serializers
from utils.permissions import InnerAPIKey


# TODO implement methods
class ContactMessageLinksAPIView(APIView):
    permission_classes = [InnerAPIKey]

    def post(self, request: Request) -> Response:
        request_data = amo_a5client.serializers.CreateMessageContactLinkSerializer(data=request.query_params)
        request_data.validate()

    def get(self, request: Request) -> Response:
        pass
