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
from .tasks import send_sms_alert


class AlertEventViewSet(viewsets.ModelViewSet):
    serializer_class = AlertEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['device', 'alert_type', 'resolved']
    http_method_names = ['get', 'post', 'put', 'head', 'options']

    def get_queryset(self):
        # Guard for drf-spectacular schema generation
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
| latitude | decimal string | ❌ | GPS latitude at time of alert e.g. `23.726008` |
| longitude | decimal string | ❌ | GPS longitude at time of alert e.g. `90.406723` |

**Alert types:**
| Value | When triggered |
|---|---|
| `PANIC` | Child pressed the SOS/panic button |
| `GEOFENCE` | Child left a defined safe zone |
| `MOTION` | Suspicious motion detected by sensor |

**What happens automatically:**
1. Alert is saved to the database
2. Celery task fires in the background:
   - Sends SMS to the parent phone (dev mode: printed in Celery terminal)
   - Pushes real-time WebSocket notification to parent dashboard:
     `{"type": "alert", "alert_type": "PANIC", "lat": "...", "lon": "..."}`
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
                value={'id': 'd4e5f6a7-...', 'device': 'b2c3d4e5-...',
                       'device_name': 'Riya School Device',
                       'alert_type': 'PANIC',
                       'alert_type_display': 'Panic Button',
                       'latitude': '23.726008', 'longitude': '90.406723',
                       'sms_sent': False, 'sms_sent_at': None,
                       'resolved': False,
                       'timestamp': '2025-01-15T14:40:00Z'}),
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
        send_sms_alert.delay(str(alert.id))
        return Response(AlertEventSerializer(alert).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary='List alerts for a device',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Optional query parameters to filter results.

**Query parameters:**
| Parameter | Example | Description |
|---|---|---|
| device | `?device=uuid` | Filter by device UUID — get from GET /api/devices/ |
| resolved | `?resolved=false` | `false` = active alerts only, `true` = resolved only |
| alert_type | `?alert_type=PANIC` | Filter by type: `PANIC`, `GEOFENCE`, or `MOTION` |

**Example URLs:**
```
GET /api/alerts/?device=uuid
GET /api/alerts/?device=uuid&resolved=false
GET /api/alerts/?device=uuid&alert_type=PANIC
GET /api/alerts/?device=uuid&resolved=false&alert_type=GEOFENCE
```

**What you get back:** Paginated list of alerts, newest first.

**Response fields:**
| Field | Type | Description |
|---|---|---|
| id | UUID | Alert ID — use for detail or resolve endpoint |
| device | UUID | Device that triggered this alert |
| device_name | string | Friendly name of the device |
| alert_type | string | `PANIC`, `GEOFENCE`, or `MOTION` |
| alert_type_display | string | Human readable: `Panic Button`, `Geofence Breach`, `Suspicious Motion` |
| latitude / longitude | decimal | Location where alert was triggered |
| sms_sent | boolean | Whether SMS was sent to parent |
| sms_sent_at | datetime / null | When the SMS was sent |
| resolved | boolean | `false` = active, `true` = parent marked resolved |
| timestamp | datetime | When the alert occurred |
        """,
        parameters=[
            OpenApiParameter('device', OpenApiTypes.UUID, OpenApiParameter.QUERY,
                description='Device UUID from GET /api/devices/'),
            OpenApiParameter('resolved', OpenApiTypes.BOOL, OpenApiParameter.QUERY,
                description='false = active alerts only, true = resolved alerts only'),
            OpenApiParameter('alert_type', OpenApiTypes.STR, OpenApiParameter.QUERY,
                description='PANIC, GEOFENCE, or MOTION', enum=['PANIC', 'GEOFENCE', 'MOTION']),
        ],
        responses={200: AlertEventSerializer(many=True)},
        examples=[
            OpenApiExample('Alerts List (200)', response_only=True, status_codes=['200'],
                value={'count': 3, 'next': None, 'previous': None, 'results': [
                    {'id': 'd4e5f6a7-...', 'device': 'b2c3d4e5-...',
                     'device_name': 'Riya School Device',
                     'alert_type': 'PANIC', 'alert_type_display': 'Panic Button',
                     'latitude': '23.726008', 'longitude': '90.406723',
                     'sms_sent': True, 'sms_sent_at': '2025-01-15T14:40:02Z',
                     'resolved': False, 'timestamp': '2025-01-15T14:40:00Z'}
                ]}),
        ],
        tags=['4. Alerts'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get a single alert by ID',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Alert UUID in the URL.

**What you get back:** Full alert object with all fields.

**Use case:** Show full alert details when a parent taps on a notification.
        """,
        responses={
            200: AlertEventSerializer,
            404: OpenApiResponse(description='Alert not found or belongs to a different user'),
        },
        tags=['4. Alerts'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Mark an alert as resolved',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Nothing in the body. Just the alert UUID in the URL.

**URL format:** `PUT /api/alerts/{alert-uuid}/resolve/`

**What you get back:**
```json
{"status": "resolved"}
```

**What changes:** The alert's `resolved` field becomes `true`.
The alert stays in the database — it will no longer appear in `?resolved=false` queries.

**Use case:** Parent receives a PANIC alert, calls the child, confirms they are safe,
then taps "Mark as Resolved" to dismiss it from the active alerts list.

**Error cases:**
| Status | Meaning |
|---|---|
| 404 | Alert UUID not found or belongs to a different user |
        """,
        request=None,
        responses={
            200: OpenApiResponse(description='Alert resolved successfully'),
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
