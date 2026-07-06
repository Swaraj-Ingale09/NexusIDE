from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create an admin user for NexusIDE Admin Dashboard (deletes previous admin)'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help='Admin username')
        parser.add_argument('--email', type=str, required=True, help='Admin email')
        parser.add_argument('--password', type=str, required=True, help='Admin password')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        try:
            # Check if this specific user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already exists. Updating to superuser.')
                )
                user = User.objects.get(username=username)
                user.is_superuser = True
                user.is_staff = True
                user.email = email
                user.set_password(password)
                user.save()
            else:
                admin_user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'Admin user "{username}" created/updated successfully!')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Email: {email}')
            )
            self.stdout.write(
                self.style.WARNING('Admin Dashboard: /admin/dashboard/html/')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating admin user: {str(e)}')
            )
