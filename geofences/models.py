import uuid
import math
from django.db import models
from devices.models import Device


class Geofence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='geofences',
        help_text='Each device has its own set of geofences.',
    )
    name = models.CharField(max_length=100)  # e.g. 'Home', 'School'
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text='Centre point latitude',
    )
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    radius_m = models.IntegerField(default=100, help_text='Radius in metres')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.device.name})'

    def contains(self, lat: float, lon: float) -> bool:
        """
        Haversine check — returns True if (lat, lon) is inside this geofence.
        Called by the ESP32 alert handler or a periodic Celery beat check.
        """
        R = 6_371_000  # Earth radius in metres
        phi1 = math.radians(float(self.latitude))
        phi2 = math.radians(lat)
        d_phi = math.radians(lat - float(self.latitude))
        d_lam = math.radians(lon - float(self.longitude))

        a = (
            math.sin(d_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
        )
        distance_m = R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return distance_m <= self.radius_m
