from rest_framework.routers import DefaultRouter
from .views import EmergencyContactViewSet

router = DefaultRouter()
router.register('contacts', EmergencyContactViewSet, basename='emergency-contact')

urlpatterns = router.urls
