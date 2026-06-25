from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from .models import EmergencyContact
from .serializers import EmergencyContactSerializer


class EmergencyContactViewSet(viewsets.ModelViewSet):
    serializer_class = EmergencyContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return EmergencyContact.objects.none()
        return EmergencyContact.objects.filter(owner=self.request.user)

    def _enforce_single_primary(self, serializer):
        """If this contact is being saved as primary, un-set primary on all others."""
        if serializer.validated_data.get('is_primary'):
            EmergencyContact.objects.filter(
                owner=self.request.user, is_primary=True
            ).exclude(pk=serializer.instance.pk if serializer.instance else None).update(
                is_primary=False
            )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        self._enforce_single_primary(serializer)

    def perform_update(self, serializer):
        serializer.save()
        self._enforce_single_primary(serializer)

    @extend_schema(
        summary='Create an emergency contact',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:**
| Field | Type | Required | Description |
|---|---|---|---|
| name | string | ✅ | Contact's name |
| phone | string | ✅ | Digits only (optionally with +, spaces, dashes), 7–15 digits |
| relation | string | ❌ | e.g. `Father`, `Mother`, `Neighbour` |
| is_primary | boolean | ❌ | Marks this as the #1 Primary Guardian contact. Setting this to `true` automatically un-sets any other primary contact you have. |

**What you get back:** The created contact, including its `id`.
        """,
        request=EmergencyContactSerializer,
        responses={
            201: EmergencyContactSerializer,
            400: OpenApiResponse(description='Validation error'),
            401: OpenApiResponse(description='Missing or invalid JWT token'),
        },
        examples=[
            OpenApiExample('Add father as emergency contact', request_only=True,
                value={'name': 'Ariful', 'phone': '01658634960', 'relation': 'Uncle', 'is_primary': False}),
            OpenApiExample('Created (201)', response_only=True, status_codes=['201'],
                value={'id': 'f1a2b3c4-...', 'name': 'Ariful', 'phone': '01658634960',
                       'relation': 'Uncle', 'is_primary': False, 'created_at': '2026-06-25T08:00:00Z'}),
        ],
        tags=['6. Emergency Contacts'],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary='List my emergency contacts',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What you get back:** All emergency contacts belonging to you, primary contact first.
        """,
        responses={200: EmergencyContactSerializer(many=True)},
        tags=['6. Emergency Contacts'],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary='Get a single emergency contact by ID',
        responses={
            200: EmergencyContactSerializer,
            404: OpenApiResponse(description='Not found or belongs to a different user'),
        },
        tags=['6. Emergency Contacts'],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary='Update an emergency contact — full update (all required fields)',
        request=EmergencyContactSerializer,
        responses={
            200: EmergencyContactSerializer,
            400: OpenApiResponse(description='Validation error'),
            404: OpenApiResponse(description='Not found'),
        },
        tags=['6. Emergency Contacts'],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary='Partially update an emergency contact (only send fields to change)',
        description="""
**Examples:**
- Rename only: `{"name": "New Name"}`
- Change phone only: `{"phone": "01711111111"}`
- Promote to primary guardian: `{"is_primary": true}`
        """,
        request=EmergencyContactSerializer,
        responses={
            200: EmergencyContactSerializer,
            404: OpenApiResponse(description='Not found'),
        },
        tags=['6. Emergency Contacts'],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary='Delete an emergency contact permanently',
        description="""
**What you get back:** `204 No Content` — empty response means success.

> ⚠️ This permanently deletes the contact. It cannot be recovered.
        """,
        request=None,
        responses={
            204: OpenApiResponse(description='Contact deleted permanently'),
            404: OpenApiResponse(description='Not found'),
        },
        tags=['6. Emergency Contacts'],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
