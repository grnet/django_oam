from django.core.management.base import BaseCommand

from utils.helper_functions import get_ends
from utils.oam_multiconnect import icinga_stats


class Command(BaseCommand):
    help = 'Inform icinga about the vpn status'

    def handle(self, *args, **options):
        ends = get_ends()
        icinga_stats(ends)
