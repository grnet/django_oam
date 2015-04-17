from django.core.management.base import BaseCommand

from utils.rrd import update_rrds


class Command(BaseCommand):
    help = 'Create graphs based in the rrds'

    def handle(self, *args, **options):
        update_rrds()
