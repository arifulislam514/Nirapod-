from rest_framework import serializers
from .models import AlertEvent


class AlertEventSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)

    class Meta:
        model = AlertEvent
        fields = (
            'id', 'device', 'device_name',
            'alert_type', 'alert_type_display',
            'latitude', 'longitude',
            'sms_sent', 'sms_sent_at',
            'resolved', 'timestamp',
        )
        read_only_fields = (
            'id', 'device', 'device_name', 'alert_type_display',
            'sms_sent', 'sms_sent_at', 'timestamp',
        )
