import uuid
from django.db import models
from devices.models import Device


class AlertEvent(models.Model):
    ALERT_TYPES = [
        ('PANIC', 'Panic Button'),
        ('GEOFENCE', 'Geofence Breach'),
        ('MOTION', 'Suspicious Motion'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='alerts',
    )
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPES)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Location at time of alert',
    )
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    sms_sent = models.BooleanField(default=False)
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    resolved = models.BooleanField(default=False)  # parent marks resolved
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', '-timestamp']),
            models.Index(fields=['resolved']),
        ]

    def __str__(self):
        return f'{self.alert_type} — {self.device.name} @ {self.timestamp:%Y-%m-%d %H:%M}'
