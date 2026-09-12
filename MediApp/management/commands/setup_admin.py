import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Ensures default admin and staff accounts exist on deploy with verified credentials'

    def handle(self, *args, **options):
        User = get_user_model()
        
        # 1. Administrator Account
        admin_user, created = User.objects.get_or_create(username='admin')
        admin_user.set_password('Neeraj@600666')
        admin_user.email = '2310074@ritindia.edu'
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.is_active = True
        admin_user.role = 'admin'
        admin_user.first_name = 'Neeraj'
        admin_user.last_name = 'Sharma'
        admin_user.save()
        self.stdout.write(self.style.SUCCESS(f"Admin user 'admin' (email: {admin_user.email}, password: Neeraj@600666) is ready."))

        # 2. Staff Pharmacist Account: Neeraj_123
        staff_user, s_created = User.objects.get_or_create(username='Neeraj_123')
        if s_created or not staff_user.has_usable_password():
            staff_user.set_password('Neeraj@600666')
        staff_user.email = '2310074@ritindia.edu'
        staff_user.role = 'pharmacist'
        staff_user.is_active = True
        staff_user.is_staff = True
        staff_user.first_name = 'Neeraj'
        staff_user.last_name = 'Staff'
        staff_user.save()
        self.stdout.write(self.style.SUCCESS(f"Staff user 'Neeraj_123' (email: 2310074@ritindia.edu) is ready."))
