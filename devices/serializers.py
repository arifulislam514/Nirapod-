import secrets
from rest_framework import serializers
from .models import Device


class DeviceSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)

    class Meta:
        model = Device
        fields = (
            'id', 'owner_email', 'name', 'device_token',
            'is_active', 'last_seen', 'battery_pct',
        )
        read_only_fields = ('id', 'owner_email', 'device_token', 'last_seen')

    def create(self, validated_data):
        # Auto-generate a secure 64-char hex token on registration
        validated_data['device_token'] = secrets.token_hex(32)
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class DeviceUpdateSerializer(serializers.ModelSerializer):
    """Only name and is_active can be updated by the parent."""

    class Meta:
        model = Device
        fields = ('name', 'is_active')
