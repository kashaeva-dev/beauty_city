from django.db import models


class Client(models.Model):
    chat_id = models.CharField(max_length=100, verbose_name='ID чата клиента')
    nickname = models.CharField(max_length=500, verbose_name='Никнейм клиента')
    name = models.CharField(max_length=40, verbose_name='Имя клиента', null=True, blank=True)
    tel_number = models.CharField(max_length=12, verbose_name='Номер телефона', null=True, blank=True, unique=True)

    def __str__(self):
        return f'#{self.pk} {self.name} {self.nickname}'


class Procedure(models.Model):
    name = models.CharField(verbose_name='Название процедуры',max_length=30)
    masters = models.ManyToManyField(Master)

    def __str__(self):
        return f'{self.name}'


class Salon(models.Model):
    name = models.CharField(verbose_name='Название салона', max_length=30)
    address = models.TextField(verbose_name='Адрес салона', blank=True, null=True)
    session = models.DateTimeField(verbose_name='Сеанс', null=True, blank=True)

    def __str__(self):
        return f'{self.name}'


class Master(models.Model):
    name = models.CharField(max_length=40, verbose_name='Имя мастера',)
    salons = models.ManyToManyField(Salon)

    def __str__(self):
        return f'{self.name}'


class Record(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    master = models.ForeignKey(Master, on_delete=models.CASCADE)
    procedure = models.ForeignKey(Procedure, on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.client} на {self.procedure} к мастеру {self.master}'
