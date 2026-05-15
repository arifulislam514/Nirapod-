from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from .serializers import UserProfileSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get my profile',
        description="""
**Authentication:** `Authorization: JWT your-access-token`

**What to send:** Nothing — just the Authorization header.

**What you get back:** Your full account profile.

| Field | Type | Description |
|---|---|---|
| id | UUID | Your account ID |
| email | string | Your login email |
| name | string | Your full name |
| phone | string | Phone number used for SMS alerts |
| role | string | `parent` for regular accounts |
| created_at | datetime | When the account was created |
        """,
        responses={
            200: UserProfileSerializer,
            401: OpenApiResponse(description='Missing or invalid JWT token'),
        },
        examples=[
            OpenApiExample(
                'Success (200)',
                response_only=True,
                status_codes=['200'],
                value={
                    'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
                    'email': 'parent@example.com',
                    'name': 'Rahim Uddin',
                    'phone': '01711111111',
                    'role': 'parent',
                    'created_at': '2025-01-15T10:30:00Z',
                },
            ),
        ],
        tags=['1. Authentication'],
    )
    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)
