from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from devices.models import Device
from .models import LocationReading
from .serializers import LocationReadingSerializer
from .services import record_location


class LocationViewSet(viewsets.ModelViewSet):
    serializer_class = LocationReadingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['device']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        # Guard for drf-spectacular schema generation
        if getattr(self, 'swagger_fake_view', False):
            return LocationReading.objects.none()
        return LocationReading.objects.filter(
            device__owner=self.request.user
        ).select_related('device')

    @extend_schema(
        summary='[ESP32 Only] Post a GPS reading',
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
| latitude | decimal string | ✅ | GPS latitude e.g. `23.726008` |
| longitude | decimal string | ✅ | GPS longitude e.g. `90.406723` |
| accuracy | float | ❌ | GPS accuracy in metres e.g. `5.0` |
| speed | float | ❌ | Speed in m/s e.g. `1.2` |
| battery_pct | integer | ❌ | Battery 0–100 e.g. `87` |

**What happens automatically:**
1. GPS reading is saved to the database
2. `Device.last_seen` and `battery_pct` are updated
3. A real-time WebSocket message is pushed to the parent dashboard:
   `{"type": "location", "lat": "...", "lon": "...", "ts": "..."}`
        """,
        request=LocationReadingSerializer,
        responses={
            201: LocationReadingSerializer,
            403: OpenApiResponse(description='X-Device-Token header missing or invalid'),
        },
        examples=[
            OpenApiExample('Request (from ESP32)', request_only=True,
                value={'latitude': '23.726008', 'longitude': '90.406723',
                       'accuracy': 5.0, 'speed': 1.2, 'battery_pct': 87}),
            OpenApiExample('Saved (201)', response_only=True, status_codes=['201'],
                value={'id': 'c3d4e5f6-...', 'device': 'b2c3d4e5-...',
                       'device_name': 'Riya School Device',
                       'latitude': '23.726008', 'longitude': '90.406723',
                       'accuracy': 5.0, 'speed': 1.2,
                       'timestamp': '2025-01-15T14:35:00Z'}),
        ],
        tags=['3. Locations'],
    )
    def create(self, request, *args, **kwargs):
        device = request.auth
        if not isinstance(device, Device):
            raise PermissionDenied(
                'This endpoint requires X-Device-Token header, not JWT.'
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reading = record_location(device, {
            'latitude': serializer.validated_data['latitude'],
            'longitude': serializer.validated_data['longitude'],
            'accuracy': serializer.validated_data.get('accuracy'),
            'speed': serializer.validated_data.get('speed'),
            'battery_pct': request.data.get('battery_pct'),
        })
        return Response(LocationReadingSerializer(reading).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary='Get location history for a device',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Pass the device UUID as a query parameter.

**Query parameters:**
| Parameter | Required | Example | Description |
|---|---|---|---|
| device | ❌ | `?device=uuid` | Filter by device UUID — get from GET /api/devices/ |

**What you get back:** Paginated list of all GPS readings, newest first.
Default 20 per page. Use `?page=2` for the next page.

**Example URLs:**
```
GET /api/locations/?device=b2c3d4e5-f6a7-8901-bcde-f12345678901
GET /api/locations/?device=b2c3d4e5-f6a7-8901-bcde-f12345678901&page=2
```
        """,
        parameters=[
            OpenApiParameter('device', OpenApiTypes.UUID, OpenApiParameter.QUERY,
                description='Device UUID from GET /api/devices/'),
        ],
        responses={200: LocationReadingSerializer(many=True)},
        tags=['3. Locations'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get a single GPS reading by its ID',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Location reading UUID in the URL.

**What you get back:** One GPS reading object.
        """,
        responses={200: LocationReadingSerializer},
        tags=['3. Locations'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Get the latest GPS position of a device',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Device UUID as a required query parameter.

**What you get back:** A single location reading — the most recent one from that device.

**Use case:** Show "where is my child right now?" on a map.

**Error cases:**
| Status | Meaning |
|---|---|
| 400 | You forgot to add `?device=uuid` |
| 404 | The device has never sent a GPS reading yet |

**Example URL:**
```
GET /api/locations/latest/?device=b2c3d4e5-f6a7-8901-bcde-f12345678901
```
        """,
        parameters=[
            OpenApiParameter('device', OpenApiTypes.UUID, OpenApiParameter.QUERY,
                description='Device UUID — required. Get from GET /api/devices/',
                required=True),
        ],
        responses={
            200: LocationReadingSerializer,
            400: OpenApiResponse(description='device query param is missing'),
            404: OpenApiResponse(description='No GPS readings found for this device yet'),
        },
        examples=[
            OpenApiExample('Success (200)', response_only=True, status_codes=['200'],
                value={'id': 'c3d4e5f6-...', 'device': 'b2c3d4e5-...',
                       'device_name': 'Riya School Device',
                       'latitude': '23.726008', 'longitude': '90.406723',
                       'accuracy': 5.0, 'speed': 1.2,
                       'timestamp': '2025-01-15T14:35:00Z'}),
            OpenApiExample('No readings yet (404)', response_only=True, status_codes=['404'],
                value={'detail': 'No GPS readings found for this device yet.'}),
        ],
        tags=['3. Locations'],
    )
    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        device_id = request.query_params.get('device')
        if not device_id:
            return Response(
                {'detail': 'device query param is required. Example: ?device=your-device-uuid'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reading = (
            LocationReading.objects
            .filter(device__id=device_id, device__owner=request.user)
            .order_by('-timestamp')
            .first()
        )
        if not reading:
            return Response(
                {'detail': 'No GPS readings found for this device yet.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(LocationReadingSerializer(reading).data)
