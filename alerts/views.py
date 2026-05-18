from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from devices.models import Device
from .models import AlertEvent
from .serializers import AlertEventSerializer
from .tasks import send_alert_notification   # plain function — no Celery


class AlertEventViewSet(viewsets.ModelViewSet):
    serializer_class = AlertEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['device', 'alert_type', 'resolved']
    http_method_names = ['get', 'post', 'put', 'head', 'options']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return AlertEvent.objects.none()
        return AlertEvent.objects.filter(
            device__owner=self.request.user
        ).select_related('device')

    @extend_schema(
        summary='[ESP32 Only] Trigger an alert event',
        description="""
**Authentication:** This endpoint uses Device Token — NOT JWT.

Add this header:
```
X-Device-Token: your-64-char-device-token
```

**Who calls this:** The ESP32 hardware only. The frontend does NOT call this.

**What to send:**
| Field | Type | Required | Description |
|---|---|---|---|
| alert_type | string | ✅ | One of: `PANIC`, `GEOFENCE`, `MOTION` |
| latitude | decimal string | ❌ | GPS latitude at time of alert |
| longitude | decimal string | ❌ | GPS longitude at time of alert |

**Alert types:**
| Value | When triggered |
|---|---|
| `PANIC` | Child pressed the SOS/panic button |
| `GEOFENCE` | Child left a defined safe zone |
| `MOTION` | Suspicious motion detected |

**What happens after posting:**
1. Alert saved to database
2. Real-time WebSocket notification pushed to parent dashboard
3. SMS is sent directly by the ESP32 SIM800L hardware (independent of this API)
        """,
        request=AlertEventSerializer,
        responses={
            201: AlertEventSerializer,
            403: OpenApiResponse(description='X-Device-Token header missing or invalid'),
            400: OpenApiResponse(description='Invalid alert_type value'),
        },
        examples=[
            OpenApiExample('Panic Button', request_only=True,
                value={'alert_type': 'PANIC',
                       'latitude': '23.726008', 'longitude': '90.406723'}),
            OpenApiExample('Geofence Breach', request_only=True,
                value={'alert_type': 'GEOFENCE',
                       'latitude': '23.810000', 'longitude': '90.500000'}),
            OpenApiExample('Motion Alert', request_only=True,
                value={'alert_type': 'MOTION',
                       'latitude': '23.726008', 'longitude': '90.406723'}),
            OpenApiExample('Alert Created (201)', response_only=True, status_codes=['201'],
                value={
                    'id': 'd4e5f6a7-...', 'device': 'b2c3d4e5-...',
                    'device_name': 'Riya School Device',
                    'alert_type': 'PANIC',
                    'alert_type_display': 'Panic Button',
                    'latitude': '23.726008', 'longitude': '90.406723',
                    'sms_sent': False, 'sms_sent_at': None,
                    'resolved': False,
                    'timestamp': '2025-01-15T14:40:00Z',
                }),
        ],
        tags=['4. Alerts'],
    )
    def create(self, request, *args, **kwargs):
        device = request.auth
        if not isinstance(device, Device):
            raise PermissionDenied(
                'This endpoint requires X-Device-Token header, not JWT.'
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alert = serializer.save(device=device)

        # Call directly — no Celery needed
        # SMS is handled by ESP32 SIM800L independently
        send_alert_notification(str(alert.id))

        return Response(AlertEventSerializer(alert).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary='List alerts for a device',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**Query parameters:**
| Parameter | Example | Description |
|---|---|---|
| device | `?device=uuid` | Filter by device UUID |
| resolved | `?resolved=false` | `false` = active alerts only |
| alert_type | `?alert_type=PANIC` | Filter by type |

**Example URLs:**
```
GET /api/alerts/?device=uuid&resolved=false
GET /api/alerts/?device=uuid&alert_type=PANIC
```
        """,
        parameters=[
            OpenApiParameter('device', OpenApiTypes.UUID, OpenApiParameter.QUERY,
                description='Device UUID from GET /api/devices/'),
            OpenApiParameter('resolved', OpenApiTypes.BOOL, OpenApiParameter.QUERY,
                description='false = active alerts, true = resolved alerts'),
            OpenApiParameter('alert_type', OpenApiTypes.STR, OpenApiParameter.QUERY,
                description='PANIC, GEOFENCE, or MOTION',
                enum=['PANIC', 'GEOFENCE', 'MOTION']),
        ],
        responses={200: AlertEventSerializer(many=True)},
        tags=['4. Alerts'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get a single alert by ID',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Alert UUID in the URL.
        """,
        responses={
            200: AlertEventSerializer,
            404: OpenApiResponse(description='Alert not found'),
        },
        tags=['4. Alerts'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Mark an alert as resolved',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**URL:** `PUT /api/alerts/{alert-uuid}/resolve/`

**Body:** Nothing required.

**Returns:** `{"status": "resolved"}`

Sets `resolved=true` on the alert. Alert stays in DB for history.
        """,
        request=None,
        responses={
            200: OpenApiResponse(description='Alert resolved'),
            404: OpenApiResponse(description='Alert not found'),
        },
        examples=[
            OpenApiExample('Success (200)', response_only=True, status_codes=['200'],
                value={'status': 'resolved'}),
        ],
        tags=['4. Alerts'],
    )
    @action(detail=True, methods=['put'], url_path='resolve')
    def resolve(self, request, pk=None):
        alert = self.get_object()
        alert.resolved = True
        alert.save(update_fields=['resolved'])
        return Response({'status': 'resolved'})
