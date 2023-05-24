from django.contrib import admin

from .models import (
    Client,
    Service,
    Salon,
    Specialist,
    Slot,
    Appointment,
)

admin.site.register(Client)
admin.site.register(Service)
admin.site.register(Salon)
admin.site.register(Specialist)
admin.site.register(Slot)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    raw_id_fields = ('slot', 'service')
