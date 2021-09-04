# Generated by Django 2.2.14 on 2021-07-12 23:09

import dillo.models.mixins
import dillo.storage
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0064_entity_hotness'),
    ]

    operations = [
        migrations.AlterField(
            model_name='staticasset',
            name='source',
            field=models.FileField(blank=True, storage=dillo.storage.S3Boto3CustomStorage(), upload_to=dillo.models.mixins.get_upload_to_hashed_path),
        ),
    ]