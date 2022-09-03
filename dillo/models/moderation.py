import logging
from django.db import models


log = logging.getLogger(__name__)


class SpamWord(models.Model):
    word = models.CharField(max_length=256, unique=True)

    def __str__(self):
        return self.word


class AllowedDomain(models.Model):
    """Top level allowed domains (no subdomains, no protocols)."""

    url = models.CharField(max_length=256, unique=True)

    def __str__(self):
        return self.url
