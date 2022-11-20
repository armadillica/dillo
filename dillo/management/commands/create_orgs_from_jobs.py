import logging

from django.core.management.base import BaseCommand

from dillo.models.cities import City
from dillo.models.jobs import Job
from dillo.models.organizations import Organization

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create organizations from jobs."

    def create_or_update_org(self, job):
        if not job.company:
            return
        self.stdout.write(self.style.SUCCESS('Processing %s') % job.company)
        try:
            Organization.objects.get(name=job.company)
            self.stdout.write(self.style.SUCCESS('Skipping existing %s') % job.company)

        except Organization.DoesNotExist:

            org = Organization.objects.create(
                name=job.company,
                visibility=Organization.Visibilities.PUBLIC,
            )
            city = City.objects.filter(name=job.city).first()
            if city:
                org.city = job.city
                org.country = city.country
                org.save()

    def handle(self, *args, **options):
        for job in Job.objects.all():
            self.create_or_update_org(job)
