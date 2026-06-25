from django.contrib import admin
from .models import EmergencyContact


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'phone', 'relation', 'is_primary', 'created_at')
    list_filter = ('is_primary',)
    search_fields = ('name', 'phone', 'owner__email')
