from rest_framework import serializers


class OauthCallbackQueryParamsSerializer(serializers.Serializer):
    code = serializers.CharField()
    referer = serializers.CharField()  # domain
    client_id = serializers.CharField()  # integration id
    state = serializers.CharField()
