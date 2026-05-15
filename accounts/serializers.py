from rest_framework import serializers
from djoser.serializers import UserCreateSerializer
from .models import CustomUser


class RegisterSerializer(UserCreateSerializer):
    # Explicitly declare re_password so drf-spectacular can introspect it
    # without trying to map it to a model field
    re_password = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )

    class Meta(UserCreateSerializer.Meta):
        model = CustomUser
        fields = ('id', 'email', 'name', 'phone', 'password', 're_password')
        read_only_fields = ('id',)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'name', 'phone', 'role', 'created_at')
        read_only_fields = fields
