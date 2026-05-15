import uuid
from django.db import models
from devices.models import Device


class LocationReading(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='location_readings',
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text='6 decimal places ≈ 0.1 m accuracy',
    )
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy = models.FloatField(null=True, blank=True, help_text='GPS accuracy in metres')
    speed = models.FloatField(null=True, blank=True, help_text='m/s from GPS')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
        ]

    def __str__(self):
        return f'{self.device.name} @ {self.timestamp:%Y-%m-%d %H:%M:%S}'
