# Generated by Django 4.2 on 2023-05-24 13:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0003_remove_service_icon'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='appointment',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='appointment', to='bot.appointment', verbose_name='Запись'),
        ),
    ]