"""
Management command to rotate API keys and JWT secrets.
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from config.api_key_rotation import get_key_rotation


class Command(BaseCommand):
    help = 'Rotate API keys and JWT secrets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['rotate-jwt', 'generate-api-key', 'revoke-api-key', 'list-keys', 'cleanup'],
            required=True,
            help='Action to perform'
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Name for the API key (required for generate-api-key)'
        )
        parser.add_argument(
            '--expires-days',
            type=int,
            default=90,
            help='Days until API key expires (default: 90)'
        )
        parser.add_argument(
            '--grace-period',
            type=int,
            default=24,
            help='Grace period in hours for JWT rotation (default: 24)'
        )

    def handle(self, *args, **options):
        rotation = get_key_rotation()
        action = options['action']

        try:
            if action == 'rotate-jwt':
                self._rotate_jwt(rotation, options)
            elif action == 'generate-api-key':
                self._generate_api_key(rotation, options)
            elif action == 'revoke-api-key':
                self._revoke_api_key(rotation, options)
            elif action == 'list-keys':
                self._list_keys(rotation)
            elif action == 'cleanup':
                self._cleanup(rotation)
        except Exception as e:
            raise CommandError(f'Error: {e}')

    def _rotate_jwt(self, rotation, options):
        """Rotate JWT secret."""
        grace_period = options['grace_period']
        
        new_secret, old_secret = rotation.rotate_jwt_secret(grace_period_hours=grace_period)
        
        self.stdout.write(
            self.style.SUCCESS(f'JWT secret rotated successfully!')
        )
        self.stdout.write(f'New secret (first 16 chars): {new_secret[:16]}...')
        self.stdout.write(f'Grace period: {grace_period} hours')
        if old_secret:
            self.stdout.write(f'Old secret will be valid until grace period expires')

    def _generate_api_key(self, rotation, options):
        """Generate a new API key."""
        name = options['name']
        expires_days = options['expires_days']
        
        if not name:
            raise CommandError('--name is required for generate-api-key')
        
        api_key = rotation.generate_api_key(name=name, expires_days=expires_days)
        
        self.stdout.write(
            self.style.SUCCESS(f'API key generated successfully!')
        )
        self.stdout.write(f'Name: {name}')
        self.stdout.write(f'Key: {api_key}')
        self.stdout.write(f'Expires: {expires_days} days')
        self.stdout.write(
            self.style.WARNING('Save this key now! It will not be shown again.')
        )

    def _revoke_api_key(self, rotation, options):
        """Revoke an API key."""
        name = options['name']
        
        if not name:
            raise CommandError('--name is required for revoke-api-key')
        
        if rotation.revoke_api_key(name):
            self.stdout.write(
                self.style.SUCCESS(f'API key "{name}" revoked successfully!')
            )
        else:
            raise CommandError(f'API key "{name}" not found')

    def _list_keys(self, rotation):
        """List active API keys."""
        active_count = rotation.get_active_keys_count()
        
        self.stdout.write(f'Active API keys: {active_count}')
        
        if rotation.keys['jwt_secrets']:
            self.stdout.write(f'JWT secrets stored: {len(rotation.keys["jwt_secrets"])}')
            for i, key_data in enumerate(rotation.keys['jwt_secrets'], 1):
                status = 'active' if key_data['is_active'] else 'inactive'
                self.stdout.write(f'  {i}. {status} - Created: {key_data["created_at"]}')
        
        if rotation.keys['api_keys']:
            self.stdout.write(f'API keys stored: {len(rotation.keys["api_keys"])}')
            for key_data in rotation.keys['api_keys']:
                status = 'active' if key_data['is_active'] else 'inactive'
                expires = key_data['expires_at']
                self.stdout.write(f'  - {key_data["name"]}: {status} (expires: {expires})')

    def _cleanup(self, rotation):
        """Clean up expired API keys."""
        removed_count = rotation.cleanup_expired_keys()
        
        if removed_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Cleaned up {removed_count} expired API keys')
            )
        else:
            self.stdout.write('No expired API keys found')
