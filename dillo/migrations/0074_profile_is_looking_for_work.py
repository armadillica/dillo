# Generated by Django 3.2.13 on 2022-11-15 21:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dillo', '0073_profile_trust_level'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='is_looking_for_work',
            field=models.BooleanField(default=False, verbose_name='Looking for work'),
        ),
    ]