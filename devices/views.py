from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from .models import Device
from .serializers import DeviceSerializer, DeviceUpdateSerializer


class DeviceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ('update', 'partial_update'):
            return DeviceUpdateSerializer
        return DeviceSerializer

    def get_queryset(self):
        # Guard for drf-spectacular schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Device.objects.none()
        return Device.objects.filter(owner=self.request.user).select_related('owner')

    @extend_schema(
        summary='Register a new ESP32 device',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Just the device name — a friendly label you choose.

**What you get back:** The new device object including the auto-generated `device_token`.

> ⚠️ **Save the `device_token` immediately.** This 64-character hex string must be
> flashed/uploaded to the ESP32 hardware. The ESP32 sends it in every request as:
> `X-Device-Token: <token>`

**Response fields:**
| Field | Type | Description |
|---|---|---|
| id | UUID | Device ID — use in all other calls as `?device=uuid` |
| owner_email | string | Your email (auto-set from JWT) |
| name | string | Friendly name you gave |
| device_token | string | 64-char hex — flash this to the ESP32 |
| is_active | boolean | `true` = can send data |
| last_seen | datetime / null | Last GPS ping. `null` = never connected |
| battery_pct | integer | Last known battery 0–100 |
        """,
        request=DeviceSerializer,
        responses={
            201: DeviceSerializer,
            401: OpenApiResponse(description='Missing or invalid JWT token'),
        },
        examples=[
            OpenApiExample('Request', request_only=True,
                value={'name': 'Riya School Device'}),
            OpenApiExample('Created (201)', response_only=True, status_codes=['201'],
                value={
                    'id': 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
                    'owner_email': 'parent@example.com',
                    'name': 'Riya School Device',
                    'device_token': 'a3f9c2e1b4d87f2e9c1a0b3d5e8f2a4c6e9b1d3f5a7c9e1b3d5f7a9c1e3b5d7',
                    'is_active': True,
                    'last_seen': None,
                    'battery_pct': 100,
                }),
        ],
        tags=['2. Devices'],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary='List all my registered devices',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Nothing.

**What you get back:** All devices registered under your account.

Use the `id` field in location/alert/geofence queries as `?device=<id>`.
        """,
        responses={200: DeviceSerializer(many=True)},
        tags=['2. Devices'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get a single device by ID',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Device UUID in the URL.

**What you get back:** Full device details including battery level and last seen time.
        """,
        responses={
            200: DeviceSerializer,
            404: OpenApiResponse(description='Device not found or does not belong to you'),
        },
        tags=['2. Devices'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Update device name and active status (full update — all fields required)',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Both fields required for PUT.

**Fields:**
| Field | Type | Required | Description |
|---|---|---|---|
| name | string | ✅ | New friendly name |
| is_active | boolean | ✅ | `true` = active, `false` = blocked |

> Setting `is_active: false` blocks the ESP32 from posting GPS/alerts.
> Token is preserved — set back to `true` to reactivate.
        """,
        request=DeviceUpdateSerializer,
        responses={200: DeviceSerializer},
        examples=[
            OpenApiExample('Request', request_only=True,
                value={'name': 'Riya Home Device', 'is_active': True}),
        ],
        tags=['2. Devices'],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary='Partially update device (only send fields you want to change)',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Only the fields you want to change. Both fields are optional with PATCH.

**Examples:**
- Only rename: `{"name": "New Name"}`
- Only deactivate: `{"is_active": false}`
        """,
        request=DeviceUpdateSerializer,
        responses={200: DeviceSerializer},
        examples=[
            OpenApiExample('Deactivate only', request_only=True, value={'is_active': False}),
            OpenApiExample('Rename only', request_only=True, value={'name': 'Home Tracker'}),
        ],
        tags=['2. Devices'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary='Deactivate a device (soft delete — data is kept)',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Device UUID in the URL. Nothing in the body.

**What you get back:** `{"detail": "Device deactivated."}`

> This does NOT permanently delete the device or its location/alert history.
> It sets `is_active = false`. To reactivate, use PATCH with `is_active: true`.
        """,
        request=None,
        responses={200: OpenApiResponse(description='Device deactivated')},
        examples=[
            OpenApiExample('Response (200)', response_only=True, status_codes=['200'],
                value={'detail': 'Device deactivated.'}),
        ],
        tags=['2. Devices'],
    )
    def destroy(self, request, *args, **kwargs):
        device = self.get_object()
        device.is_active = False
        device.save(update_fields=['is_active'])
        return Response({'detail': 'Device deactivated.'}, status=status.HTTP_200_OK)
