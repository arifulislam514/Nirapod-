from rest_framework.routers import DefaultRouter
from .views import GeofenceViewSet

router = DefaultRouter()
router.register('geofences', GeofenceViewSet, basename='geofence')

urlpatterns = router.urls
