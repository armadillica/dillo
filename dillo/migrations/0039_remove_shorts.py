# Generated by Django 2.2.11 on 2021-01-03 02:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0038_rename_short_user_relation'),
    ]

    operations = [
        migrations.DeleteModel(name='Short',),
    ]
