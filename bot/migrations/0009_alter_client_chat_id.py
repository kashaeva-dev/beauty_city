# Generated by Django 4.2 on 2023-05-26 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0008_alter_client_phonenumber'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='chat_id',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='ID чата клиента'),
        ),
    ]
