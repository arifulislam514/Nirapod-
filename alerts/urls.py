from rest_framework.routers import DefaultRouter
from .views import AlertEventViewSet

router = DefaultRouter()
router.register('alerts', AlertEventViewSet, basename='alert')

urlpatterns = router.urls
