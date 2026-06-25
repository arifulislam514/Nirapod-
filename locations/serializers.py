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

    def validate_latitude(self, value):
        if value is None or not (-90 <= value <= 90):
            raise serializers.ValidationError('Latitude must be between -90 and 90.')
        return value

    def validate_longitude(self, value):
        if value is None or not (-180 <= value <= 180):
            raise serializers.ValidationError('Longitude must be between -180 and 180.')
        return value

    def validate_accuracy(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Accuracy cannot be negative.')
        return value

    def validate_speed(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Speed cannot be negative.')
        return value
