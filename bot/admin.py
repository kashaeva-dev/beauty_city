from django.contrib import admin
from django.db import transaction
from django.db.utils import IntegrityError
from .models import (
    Client,
    Service,
    Salon,
    Specialist,
    Slot,
    Appointment,
    Payment,
    Review,
    Promocode,
)

admin.site.register(Client)
admin.site.register(Service)
admin.site.register(Salon)
admin.site.register(Specialist)
admin.site.register(Review)
admin.site.register(Promocode)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    raw_id_fields = ('slot', 'service')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    readonly_fields = (
        'amount',
        'date',
        'appointment',
    )


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = (
        'start_date',
        'start_time',
        'specialist',
    )
    list_filter = (
        'specialist',
        'start_date',
    )
    ordering = (
        'start_date',
        'start_time',
    )
    empty_value_display = '-пусто-'

    def save_model(self, request, obj, form, change):
        try:
            with transaction.atomic(using='default'):
                obj.save()
        except IntegrityError:
            error_message = "Данное время уже существует"
            self.message_user(request, error_message)

