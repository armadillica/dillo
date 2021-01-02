from django.db import models


class Software(models.Model):
    name = models.CharField(max_length=128)

    # TODO(fsiddi) Add url, and logo/favicon

    def __str__(self):
        return self.name
