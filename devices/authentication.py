from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class DeviceTokenAuthentication(BaseAuthentication):
    """
    ESP32 devices send a static 64-char token in the custom HTTP header:
        X-Device-Token: <token>

    On success returns (device.owner, device) so:
        request.user  = the parent CustomUser account
        request.auth  = the Device instance
    """

    def authenticate(self, request):
        token = request.headers.get('X-Device-Token')
        if not token:
            return None  # fall through to JWT

        from .models import Device
        try:
            device = Device.objects.select_related('owner').get(
                device_token=token,
                is_active=True,
            )
        except Device.DoesNotExist:
            raise AuthenticationFailed('Invalid or inactive device token.')

        return (device.owner, device)

    def authenticate_header(self, request):
        return 'X-Device-Token'


# ── drf-spectacular extension ──────────────────────────────────────────────────
# Registers DeviceTokenAuthentication so Swagger knows about it and
# stops showing the warning "could not resolve authenticator".

class DeviceTokenScheme(OpenApiAuthenticationExtension):
    target_class = 'devices.authentication.DeviceTokenAuthentication'
    name = 'DeviceTokenAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-Device-Token',
            'description': (
                'ESP32 hardware device token (64-char hex string). '
                'Get it from POST /api/devices/ when registering a device. '
                'Used only for POST /api/locations/ and POST /api/alerts/.'
            ),
        }
