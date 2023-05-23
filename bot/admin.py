from django.contrib import admin

from .models import Client
from .models import Procedure
from .models import Salon
from .models import Master
from .models import Schedule
from .models import Record

admin.site.register(Client)
admin.site.register(Procedure)
admin.site.register(Salon)
admin.site.register(Master)
admin.site.register(Schedule)
admin.site.register(Record)
# Register your models here.
