from django.core.management.base import BaseCommand
from django.core.mail import send_mail

from utils.helper_functions import diff_carrier


class Command(BaseCommand):
    help = 'Check if the configuration in the database agrees with the applied one and replace it in case it does not.'

    def handle(self, *args, **options):
        message = diff_carrier()
        if message:
            send_mail(
                'Oam configuration applier',
                message,
                'noreply@example.com',
                [
                    # 'email_address1',
                    # 'email_address2',
                ],
                fail_silently=False
            )
