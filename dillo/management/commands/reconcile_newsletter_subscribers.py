from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from dillo.tasks import update_mailing_list_subscription


class Command(BaseCommand):
    help = 'Ensure newsletter settings are respected for each user.'

    def handle(self, *args, **options):
        users_count = 0
        for user in User.objects.all():
            if not user.profile.is_verified:
                self.style.NOTICE('Skipping unverified profile for user %s') % user.username
                continue
            self.style.NOTICE('Updating settings for %s') % user.username
            update_mailing_list_subscription(user.email)
            users_count += 1
        self.stdout.write(self.style.SUCCESS('%i users updated') % users_count)
