import logging

from django.core.management.base import BaseCommand
from django.db import connection
from dillo.models.posts import Post

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate existing posts to be PostWithMedia"

    def handle(self, *args, **options):
        post_count = 0
        with connection.cursor() as cursor:
            for post in Post.objects.all():
                cursor.execute("INSERT INTO dillo_postwithmedia VALUES (%s)", [post.id])

                # PostWithMedia.objects.create(post_ptr_id=post.id)
                post_count += 1
        self.stdout.write(self.style.SUCCESS('Migrated %s posts' % post_count))
