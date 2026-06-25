from rest_framework import serializers
from .models import EmergencyContact


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = (
            'id', 'name', 'phone', 'relation', 'is_primary', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate_phone(self, value):
        digits_only = value.replace('+', '').replace(' ', '').replace('-', '')
        if not digits_only.isdigit():
            raise serializers.ValidationError(
                'Phone number must contain digits only (optionally with +, spaces, or dashes).'
            )
        if not (7 <= len(digits_only) <= 15):
            raise serializers.ValidationError(
                'Phone number must be between 7 and 15 digits.'
            )
        return value

    def validate(self, attrs):
        """Only one primary contact per owner — demoting is automatic, not blocked."""
        return attrs
