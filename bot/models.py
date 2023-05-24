from django.core.exceptions import ValidationError
from django.db import models
import datetime


class Client(models.Model):
    chat_id = models.CharField(max_length=100, verbose_name='ID чата клиента', null=True, blank=True, unique=True)
    name = models.CharField(max_length=40, verbose_name='Имя клиента', null=True, blank=True)
    phonenumber = models.CharField(max_length=12, verbose_name='Номер телефона', null=True, blank=True, unique=True)

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'

    def __str__(self):
        return f'#{self.pk} {self.name}'


class Salon(models.Model):
    name = models.CharField(verbose_name='Название салона', max_length=30)
    address = models.TextField(verbose_name='Адрес салона', blank=True, null=True)

    class Meta:
        verbose_name = 'Салон'
        verbose_name_plural = 'Салоны'

    def __str__(self):
        return self.name


class Service(models.Model):
    name = models.CharField(verbose_name='Название услуги',max_length=30)
    price = models.IntegerField(verbose_name='Цена услуги', blank=True, null=True)

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'

    def __str__(self):
        return self.name


class Specialist(models.Model):
    name = models.CharField(max_length=40, verbose_name='Имя мастера',)
    surname = models.CharField(max_length=40, verbose_name='Фамилия мастера')
    salons = models.ManyToManyField(Salon)
    services = models.ManyToManyField(Service)

    class Meta:
        verbose_name = 'Мастер'
        verbose_name_plural = 'Мастера'

    def __str__(self):
        return f'{self.name} {self.surname}'


class Slot(models.Model):
    START_TIME_CHOICES = [
        ('09:00', '09:00'),
        ('09:30', '09:30'),
        ('10:00', '10:00'),
        ('10:30', '10:30'),
        ('11:00', '11:00'),
        ('11:30', '11:30'),
        ('12:00', '12:00'),
        ('12:30', '12:30'),
        ('13:00', '13:00'),
        ('13:30', '13:30'),
        ('14:00', '14:00'),
        ('14:30', '14:30'),
        ('15:00', '15:00'),
        ('15:30', '15:30'),
        ('16:00', '16:00'),
        ('16:30', '16:30'),
        ('17:00', '17:00'),
        ('17:30', '17:30'),
        ('18:00', '18:00'),
        ('18:30', '18:30'),
        ('19:00', '19:00'),
        ('19:30', '19:30'),
        ('20:00', '20:00'),
        ('20:30', '20:30'),
    ]
    start_date = models.DateField(verbose_name='Дата начала')
    start_time = models.TimeField(verbose_name='Время начала', blank=True)
    start_time_choice = models.CharField(
        verbose_name='Время начала',
        choices=START_TIME_CHOICES,
        max_length=5,
    )
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Слот'
        verbose_name_plural = 'Слоты'
        constraints = [models.UniqueConstraint(fields=['start_date', 'start_time', 'specialist'], name='unique_slot',
                                               violation_error_message="Данное время уже существует")
                       ]

    def __str__(self):
        formatted_date = self.start_date.strftime('%d.%m.%Y')
        formatted_time = self.start_time.strftime('%H:%M')
        return f'{formatted_date} {formatted_time} {self.specialist}'

    def save(self, *args, **kwargs):
        if self.start_time_choice:
            self.start_time = datetime.time(
                hour=int(self.start_time_choice[:2]),
                minute=int(self.start_time_choice[3:])
            )
        super().save(*args, **kwargs)


class Appointment(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент', related_name='appointments')
    slot = models.OneToOneField(Slot, on_delete=models.CASCADE, verbose_name='Слот', related_name='appointment')
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        verbose_name='Услуга',
        related_name='appointments',
    )

    class Meta:
        verbose_name = 'Запись'
        verbose_name_plural = 'Записи'

    def __str__(self):
        return f'{self.client.name} к мастеру {self.slot.specialist.name} {self.slot.specialist.surname} ({self.service.name}, {self.slot.start_date} {self.slot.start_time}'


class Payment(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент', related_name='payments')
    amount = models.IntegerField(verbose_name='Сумма платежа', blank=True, null=True)
    date = models.DateTimeField(verbose_name='Дата платежа', null=True, blank=True)
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        verbose_name='Запись',
        related_name='appointment',
        )

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'

    def __str__(self):
        return f'{self.date}: {self.amount} - {self.client}'


class Promocode(models.Model):
    name = models.CharField(max_length=30, verbose_name='Промокод')
    description = models.TextField(verbose_name='Описание', blank=True, null=True)
    start_date = models.DateTimeField(verbose_name='Дата начала', null=True, blank=True)
    end_date = models.DateTimeField(verbose_name='Дата окончания', null=True, blank=True)
    discount = models.IntegerField(verbose_name='Скидка, %', blank=True, null=True)

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date and self.end_date and self.end_date <= self.start_date:
            raise ValidationError('Дата окончания должна быть больше даты начала')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)



    # class Meta:
    #     constraints = (
    #         models.UniqueTogetherConstraint(
    #             fields=('master', 'schedule'),
    #             name='unique_record'
    #         ),
    #     )
