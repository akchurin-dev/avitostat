from rest_framework import serializers


class CreateMessageContactLinkSerializer(serializers.Serializer):
    amo_account_id = serializers.IntegerField()
    contact_id = serializers.IntegerField()
    message_created_at_ts = serializers.IntegerField()
    text = serializers.CharField()
    trace_id = serializers.CharField()
