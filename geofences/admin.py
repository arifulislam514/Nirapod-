from django.contrib import admin
from .models import Geofence


@admin.register(Geofence)
class GeofenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'device', 'latitude', 'longitude', 'radius_m', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'device__name', 'device__owner__email')
