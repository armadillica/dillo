import logging

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from dillo.models.mixins import CreatedUpdatedMixin

log = logging.getLogger(__name__)


class ContentReports(models.Model):
    limit = models.Q(app_label='dillo', model='Post') | models.Q(app_label='dillo', model='Comment')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, limit_choices_to=limit, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()
    reason = models.CharField(max_length=20)
    notes = models.TextField(max_length=512, blank=True)


class MessageContact(CreatedUpdatedMixin, models.Model):
    """A message sent to the admin via the Contact form."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
