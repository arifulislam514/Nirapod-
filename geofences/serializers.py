from rest_framework import serializers
from .models import Geofence


class GeofenceSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = Geofence
        fields = (
            'id', 'device', 'device_name',
            'name', 'latitude', 'longitude', 'radius_m', 'is_active',
        )
        read_only_fields = ('id', 'device_name')

    def validate_device(self, device):
        """Ensure the parent can only create geofences on their own devices."""
        request = self.context['request']
        if device.owner != request.user:
            raise serializers.ValidationError('You do not own this device.')
        return device

    def validate_latitude(self, value):
        if value is None or not (-90 <= value <= 90):
            raise serializers.ValidationError('Latitude must be between -90 and 90.')
        return value

    def validate_longitude(self, value):
        if value is None or not (-180 <= value <= 180):
            raise serializers.ValidationError('Longitude must be between -180 and 180.')
        return value

    def validate_radius_m(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError('Radius must be a positive number of metres.')
        if value > 50000:
            raise serializers.ValidationError('Radius must not exceed 50000 metres.')
        return value
