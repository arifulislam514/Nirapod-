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
