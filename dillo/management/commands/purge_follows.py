from actstream.models import Follow
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import connection
from dillo.models.posts import Post, Comment


class Command(BaseCommand):
    help = 'Deletes Follow entries with to target_object'

    def handle(self, *args, **options):
        delete_count = 0
        for follow in Follow.objects.all():
            if not follow.follow_object:
                execute_raw_query = False
                try:
                    follow.delete()
                except Post.DoesNotExist:
                    self.stdout.write(
                        self.style.NOTICE('Post %s already deleted') % follow.object_id
                    )
                    execute_raw_query = True
                except User.DoesNotExist:
                    self.stdout.write(
                        self.style.NOTICE('User %s already deleted') % follow.object_id
                    )
                    execute_raw_query = True
                except Comment.DoesNotExist:
                    self.stdout.write(
                        self.style.NOTICE('Comment %s already deleted') % follow.object_id
                    )
                    execute_raw_query = True
                if execute_raw_query:
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE from actstream_follow WHERE id = %s", [follow.id])
                        self.stdout.write(self.style.NOTICE('Deleting Activity %i') % follow.id)
                delete_count += 1
        if delete_count > 0:
            self.stdout.write(self.style.SUCCESS('Successfully deleted %i follows' % delete_count))
        else:
            self.stdout.write(self.style.SUCCESS('Now follows deleted'))
