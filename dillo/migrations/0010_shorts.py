# Generated by Django 2.2.2 on 2020-03-03 00:59

import dillo.models.mixins
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dillo', '0009_contact_message'),
    ]

    operations = [
        migrations.CreateModel(
            name='Short',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(auto_now_add=True, verbose_name='date created'),
                ),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='date edited')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(null=True)),
                ('url', models.URLField(max_length=120)),
                (
                    'visibility',
                    models.CharField(
                        choices=[('public', 'Public'), ('unlisted', 'Unlisted')],
                        default='public',
                        max_length=20,
                    ),
                ),
                (
                    'image',
                    models.ImageField(
                        blank=True,
                        height_field='image_height',
                        upload_to=dillo.models.mixins.get_upload_to_hashed_path,
                        width_field='image_width',
                    ),
                ),
                ('image_height', models.PositiveIntegerField(null=True)),
                ('image_width', models.PositiveIntegerField(null=True)),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={'abstract': False,},
        ),
    ]
