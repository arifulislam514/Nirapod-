from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from .models import Geofence
from .serializers import GeofenceSerializer


class GeofenceViewSet(viewsets.ModelViewSet):
    serializer_class = GeofenceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['device', 'is_active']

    def get_queryset(self):
        # Guard for drf-spectacular schema generation
        if getattr(self, 'swagger_fake_view', False):
            return Geofence.objects.none()
        return Geofence.objects.filter(
            device__owner=self.request.user
        ).select_related('device')

    @extend_schema(
        summary='Create a geofence (safe zone)',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What is a geofence?**
A circular safe zone defined by a centre point (lat/lon) and a radius in metres.
If the ESP32 device moves outside this circle, it triggers a `GEOFENCE` alert.

**What to send:**
| Field | Type | Required | Description |
|---|---|---|---|
| device | UUID | ✅ | UUID of the device. Get from GET /api/devices/ |
| name | string | ✅ | Friendly label e.g. `Home`, `School` |
| latitude | decimal string | ✅ | Centre point latitude e.g. `23.726008` |
| longitude | decimal string | ✅ | Centre point longitude e.g. `90.406723` |
| radius_m | integer | ✅ | Radius in metres. e.g. `150` = 150m circle |
| is_active | boolean | ✅ | `true` = enforced, `false` = temporarily disabled |

**Tip:** Right-click any location in Google Maps to copy its coordinates.

**Recommended radius values:**
- Home: 100–150 metres
- School: 200–300 metres
        """,
        request=GeofenceSerializer,
        responses={
            201: GeofenceSerializer,
            400: OpenApiResponse(description='Validation error or device not owned by you'),
            401: OpenApiResponse(description='Missing or invalid JWT token'),
        },
        examples=[
            OpenApiExample('Create Home Zone', request_only=True,
                value={'device': 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
                       'name': 'Home', 'latitude': '23.726008',
                       'longitude': '90.406723', 'radius_m': 150, 'is_active': True}),
            OpenApiExample('Create School Zone', request_only=True,
                value={'device': 'b2c3d4e5-f6a7-8901-bcde-f12345678901',
                       'name': 'School', 'latitude': '23.730000',
                       'longitude': '90.410000', 'radius_m': 250, 'is_active': True}),
            OpenApiExample('Created (201)', response_only=True, status_codes=['201'],
                value={'id': 'e5f6a7b8-...', 'device': 'b2c3d4e5-...',
                       'device_name': 'Riya School Device',
                       'name': 'Home', 'latitude': '23.726008',
                       'longitude': '90.406723', 'radius_m': 150, 'is_active': True}),
            OpenApiExample('Wrong device (400)', response_only=True, status_codes=['400'],
                value={'device': ['You do not own this device.']}),
        ],
        tags=['5. Geofences'],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary='List all geofences for a device',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**Query parameters:**
| Parameter | Example | Description |
|---|---|---|
| device | `?device=uuid` | Filter by device UUID |
| is_active | `?is_active=true` | Show only active or only inactive fences |

**Example URLs:**
```
GET /api/geofences/?device=b2c3d4e5-f6a7-8901-bcde-f12345678901
GET /api/geofences/?device=uuid&is_active=true
```

**What you get back:** All geofences with centre points and radius.
Use `latitude`, `longitude`, and `radius_m` to draw circles on a map.
        """,
        parameters=[
            OpenApiParameter('device', OpenApiTypes.UUID, OpenApiParameter.QUERY,
                description='Device UUID from GET /api/devices/'),
            OpenApiParameter('is_active', OpenApiTypes.BOOL, OpenApiParameter.QUERY,
                description='true = active fences only, false = disabled fences only'),
        ],
        responses={200: GeofenceSerializer(many=True)},
        tags=['5. Geofences'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get a single geofence by ID',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Geofence UUID in the URL.

**What you get back:** Full geofence object with centre point and radius.
        """,
        responses={
            200: GeofenceSerializer,
            404: OpenApiResponse(description='Geofence not found or belongs to a different user'),
        },
        tags=['5. Geofences'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Update a geofence — full update (all fields required)',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** All fields required for PUT.

**Use cases:**
- Increase/decrease safe zone radius
- Move the centre point
- Rename the geofence

**Fields:**
| Field | Type | Required |
|---|---|---|
| device | UUID | ✅ |
| name | string | ✅ |
| latitude | decimal string | ✅ |
| longitude | decimal string | ✅ |
| radius_m | integer | ✅ |
| is_active | boolean | ✅ |
        """,
        request=GeofenceSerializer,
        responses={
            200: GeofenceSerializer,
            400: OpenApiResponse(description='Validation error'),
            404: OpenApiResponse(description='Geofence not found'),
        },
        examples=[
            OpenApiExample('Expand school radius', request_only=True,
                value={'device': 'b2c3d4e5-...', 'name': 'School',
                       'latitude': '23.730000', 'longitude': '90.410000',
                       'radius_m': 400, 'is_active': True}),
        ],
        tags=['5. Geofences'],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary='Partially update a geofence (only send fields you want to change)',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Only the fields you want to change. All fields optional with PATCH.

**Examples:**
- Change radius only: `{"radius_m": 300}`
- Disable only: `{"is_active": false}`
- Rename only: `{"name": "New School"}`
        """,
        request=GeofenceSerializer,
        responses={
            200: GeofenceSerializer,
            404: OpenApiResponse(description='Geofence not found'),
        },
        examples=[
            OpenApiExample('Disable fence', request_only=True, value={'is_active': False}),
            OpenApiExample('Change radius', request_only=True, value={'radius_m': 300}),
        ],
        tags=['5. Geofences'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary='Delete a geofence permanently',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Geofence UUID in the URL. Nothing in the body.

**What you get back:** `204 No Content` — empty response means success.

> ⚠️ This permanently deletes the geofence. It cannot be recovered.
> To temporarily stop enforcing it without deleting, use PATCH with `is_active: false`.
        """,
        request=None,
        responses={
            204: OpenApiResponse(description='Geofence deleted permanently'),
            404: OpenApiResponse(description='Geofence not found'),
        },
        tags=['5. Geofences'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
