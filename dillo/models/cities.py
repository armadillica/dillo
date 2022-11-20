from django.db import models


class City(models.Model):
    """Cities of the world.

    Populated in migration 0006.
    """

    name = models.CharField(max_length=256)
    name_ascii = models.CharField(max_length=256)
    lat = models.FloatField(verbose_name='latitude')
    lng = models.FloatField(verbose_name='longitude')
    country = models.CharField(max_length=2)

    def __str__(self):
        return self.name
