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
from django.utils.translation import gettext_lazy as _
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s', level=logging.DEBUG,
)

logger = logging.getLogger(__name__)


class ByServiceFilter(admin.SimpleListFilter):
    title = _('Услуга')
    parameter_name = 'specialist'

    def lookups(self, request, model_admin):
        services = Service.objects.all()
        logger.info('список услуг %s', services)
        filters = []
        for service in services:
            all_ids = []
            all_ids.append(service.pk)
            filters.append((service.pk, service.name))

        return filters if filters else None

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(specialist__in=Specialist.objects.filter(services__in=Service.objects.filter(pk=self.value())))
        else:
            return queryset

admin.site.register(Client)
admin.site.register(Salon)
admin.site.register(Specialist)
admin.site.register(Review)
admin.site.register(Promocode)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_filter = (
        'specialists',
    )


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
    ordering = (
        'start_date',
        'start_time',
    )
    list_filter = (
        ByServiceFilter,
        'specialist',
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
