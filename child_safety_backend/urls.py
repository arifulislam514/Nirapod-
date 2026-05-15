from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from accounts.views import MeView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Swagger docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/',   SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/',  SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),

    # Custom endpoint with docs
    path('api/auth/users/me/', MeView.as_view(), name='auth-me'),

    # Full Djoser — all user management routes (register, login, password reset, etc.)
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.jwt')),

    # App routes
    path('api/', include('devices.urls')),
    path('api/', include('locations.urls')),
    path('api/', include('alerts.urls')),
    path('api/', include('geofences.urls')),
]
