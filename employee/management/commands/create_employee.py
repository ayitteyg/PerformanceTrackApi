# your_app/management/commands/create_single_employee.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from employee.models import Employee

class Command(BaseCommand):
    help = 'Create a single user and employee with hardcoded details'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        contact = '0276349238'  # Hardcoded username and contact

        # Check if user already exists
        if User.objects.filter(username=contact).exists():
            self.stdout.write(self.style.WARNING(f"⚠️ User {contact} already exists. Skipping user creation."))
            return

        # Create user
        user = User.objects.create_user(username=contact, password='ofankor@25')
        self.stdout.write(self.style.SUCCESS(f"✅ User {contact} created successfully."))

        # Check if employee already exists
        if Employee.objects.filter(contact=contact).exists():
            self.stdout.write(self.style.WARNING(f"⚠️ Employee with contact {contact} already exists. Skipping employee creation."))
            return

        # Create employee
        employee = Employee.objects.create(
            user=user,
            name='Mr. Solomon',
            gender='male',  # Must match your GENDER_CHOICES
            contact=contact,
            dob='1989-01-01',
            location='Accra',
            guarantor_name='Jane Smith',
            guarantor_contact='0540000001',
            job_description='manager',  # Must match your JOB_DESCRIPTION_CHOICES
            date_employed='2025-06-01',
            training_start='2025-06-02',
            training_end='2025-06-10',
            ssnit='SSNIT123456',
            account='1234567890',
            status='active',  # Must match your STATUS_CHOICES
            site='ofankor'  # Must match your SITE_CHOICES
        )

        self.stdout.write(self.style.SUCCESS(f"✅ Employee {employee.name} created successfully."))
