from django.core.management.base import BaseCommand
from utils.oam_multiconnect import oam_icinga_config


class Command(BaseCommand):
    help = 'Create icinga configuration for oam. use "./manage.py oam_nadjicing with-hosts" to include hosts in the configuration.'

    def handle(self, *args, **options):
        print oam_icinga_config('with-hosts' in args)
