from rest_framework import serializers
from .models import LocationReading


class LocationReadingSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.name', read_only=True)

    class Meta:
        model = LocationReading
        fields = (
            'id', 'device', 'device_name',
            'latitude', 'longitude', 'accuracy', 'speed', 'timestamp',
        )
        read_only_fields = ('id', 'device', 'device_name', 'timestamp')
