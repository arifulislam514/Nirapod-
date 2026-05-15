from django.urls import re_path
from .consumers import DeviceConsumer

websocket_urlpatterns = [
    re_path(r'^ws/device/(?P<device_id>[^/]+)/$', DeviceConsumer.as_asgi()),
]
