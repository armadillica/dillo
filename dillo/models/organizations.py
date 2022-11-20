from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django_countries.fields import CountryField

from dillo.models.cities import City

from dillo.models.mixins import (
    CreatedUpdatedMixin,
    get_upload_to_hashed_path,
)


class OrganizationCategory(models.Model):
    name = models.CharField(max_length=128, unique=True)

    class Meta:
        verbose_name_plural = 'Organization categories'

    def __str__(self):
        return self.name


class Organization(CreatedUpdatedMixin, models.Model):
    class Visibilities(models.TextChoices):
        PUBLIC = 'public', 'Public'
        UNLISTED = 'unlisted', 'Unlisted'
        REVIEW = 'under_review', 'Under Review'

    name = models.CharField(max_length=255, unique=True)
    visibility = models.CharField(
        max_length=16,
        choices=Visibilities.choices,
        default=Visibilities.REVIEW,
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text='A description of the organization activities.',
    )
    website = models.URLField(max_length=120)
    logo = models.ImageField(
        upload_to=get_upload_to_hashed_path,
        blank=True,
        height_field='logo_height',
        width_field='logo_width',
        help_text='A square picture, around 512x512.',
    )
    logo_height = models.PositiveIntegerField(null=True)
    logo_width = models.PositiveIntegerField(null=True)
    city = models.CharField(max_length=256, blank=True, null=True)
    city_ref = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='organizations',
        null=True,
        blank=True,
    )
    country = CountryField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_online = models.BooleanField(
        default=False,
        help_text='Operates fully online, with no physical HQ.',
    )
    is_active = models.BooleanField(default=True)
    categories = models.ManyToManyField(
        OrganizationCategory,
        null=True,
        help_text='Keywords to identify this organization.',
    )

    @property
    def location_label(self):
        if self.city and self.country:
            return f"{self.city}, {self.country.name}"
        elif self.country:
            return self.country.name
        else:
            return ''

    def get_absolute_url(self):
        return reverse('organization-update', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        # Look up city in the City table and try to associate it
        self.city_ref = City.objects.filter(name__iexact=self.city).first()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
