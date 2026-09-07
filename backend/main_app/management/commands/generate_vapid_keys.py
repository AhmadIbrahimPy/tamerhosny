import base64

from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand
from py_vapid import Vapid02


def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


class Command(BaseCommand):
    """Generates a VAPID key pair for Web Push and prints it in the
    exact env-var form settings.py reads (VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY)
    - a one-time setup step, not something run as part of normal deploys.
    """
    help = 'Generate a VAPID key pair for Web Push notifications.'

    def handle(self, *args, **options):
        vapid = Vapid02()
        vapid.generate_keys()

        private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, 'big')
        public_raw = vapid.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )

        self.stdout.write('Add these to the environment (e.g. credentials/.env):\n')
        self.stdout.write(f'VAPID_PUBLIC_KEY={_b64url(public_raw)}')
        self.stdout.write(f'VAPID_PRIVATE_KEY={_b64url(private_raw)}')
