from django.core.exceptions import ValidationError
from django.db import models
import datetime


class Client(models.Model):
    chat_id = models.CharField(max_length=100, verbose_name='ID чата клиента', null=True, blank=True, unique=True)
    name = models.CharField(max_length=40, verbose_name='Имя клиента', null=True, blank=True)
    phonenumber = models.CharField(max_length=12, verbose_name='Номер телефона', null=True, blank=True, unique=True)

    def __str__(self):
        return f'#{self.pk} {self.name}'


class Salon(models.Model):
    name = models.CharField(verbose_name='Название салона', max_length=30)
    address = models.TextField(verbose_name='Адрес салона', blank=True, null=True)


    def __str__(self):
        return f'{self.name}'


class Service(models.Model):
    name = models.CharField(verbose_name='Название услуги',max_length=30)
    price = models.IntegerField(verbose_name='Цена услуги', blank=True, null=True)

    def __str__(self):
        return f'{self.name}'


class Specialist(models.Model):
    name = models.CharField(max_length=40, verbose_name='Имя мастера',)
    surname = models.CharField(max_length=40, verbose_name='Фамилия мастера')
    salons = models.ManyToManyField(Salon)
    services = models.ManyToManyField(Service)

    def __str__(self):
        return f'{self.name}'


class Slot(models.Model):
    start_time = models.DateTimeField(verbose_name='Время начала', null=True, blank=True)
    duration = models.IntegerField(
        verbose_name='Длительность',
        null=True,
        blank=True,
        help_text='Длительность в минутах',
        default=datetime.timedelta(minutes=30),
    )
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.start_time} {self.specialist} {self.salon}'





class Appointment(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент', related_name='appointments')
    slot = models.OneToOneField(Slot, on_delete=models.CASCADE, verbose_name='Слот', related_name='appointment')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name='Услуга', related_name='appointments')

    class Meta:
        verbose_name = 'Запись'
        verbose_name_plural = 'Записи'

    def __str__(self):
        return f'{self.client.name} на {self.service.name} к мастеру {self.slot.specialist.name}{self.slot.specialist.surname}'


class Payment(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='Клиент', related_name='payments')
    amount = models.IntegerField(verbose_name='Сумма платежа', blank=True, null=True)
    date = models.DateTimeField(verbose_name='Дата платежа', null=True, blank=True)
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        verbose_name='Оплата',
        related_name='payment',
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
