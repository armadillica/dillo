# Generated by Django 2.2.14 on 2021-05-24 23:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0059_image_entity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='job', name='notes', field=models.TextField(blank=True, null=True),
        ),
    ]
