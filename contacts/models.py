import uuid
from django.db import models
from accounts.models import CustomUser


class EmergencyContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='emergency_contacts',
        help_text='The parent account this contact belongs to.',
    )
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, help_text='Used for SOS dispatch / TEST SMS.')
    relation = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g. 'Father', 'Mother', 'Neighbour' — free text.",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text='Primary guardian contact (e.g. #1 - PRIMARY GUARDIAN). Only one per owner.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'name']

    def __str__(self):
        return f'{self.name} ({self.owner.email})'
