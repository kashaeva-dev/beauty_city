from django.db import models
import datetime


class Client(models.Model):
    chat_id = models.CharField(max_length=100, verbose_name='ID чата клиента')
    nickname = models.CharField(max_length=500, verbose_name='Никнейм клиента')
    name = models.CharField(max_length=40, verbose_name='Имя клиента', null=True, blank=True)
    tel_number = models.CharField(max_length=12, verbose_name='Номер телефона', null=True, blank=True, unique=True)

    def __str__(self):
        return f'#{self.pk} {self.name} {self.nickname}'


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


class Master(models.Model):
    name = models.CharField(max_length=40, verbose_name='Имя мастера',)
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
    master = models.ForeignKey(Master, on_delete=models.CASCADE)
    salon = models.ForeignKey(Salon, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.session} {self.master} {self.salon}'



class Record(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    slot = models.ForeignKey(Slot, on_delete=models.CASCADE, verbose_name='Слот', related_name='records')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # class Meta:
    #     constraints = (
    #         models.UniqueTogetherConstraint(
    #             fields=('master', 'schedule'),
    #             name='unique_record'
    #         ),
    #     )



    def __str__(self):
        return f'{self.client} на {self.procedure} к мастеру {self.master}'
