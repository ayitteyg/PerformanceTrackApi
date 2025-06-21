# your_app/management/commands/create_employees.py

import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from employee.models import Employee

class Command(BaseCommand):
    help = 'Bulk create users and employees from JSON file'

    def handle(self, *args, **kwargs):
        try:
            with open('data_json/employees_data.json', 'r') as f:
                employees_list = json.load(f)
            self.bulk_create_employees(employees_list)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("❌ File not found: data_json/employees_data.json"))
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("❌ Invalid JSON format."))

    def bulk_create_employees(self, employees_list):
        User = get_user_model()
        new_users = []
        new_employees = []

        # Fetch existing usernames from the database
        existing_usernames = set(User.objects.filter(
            username__in=[e['contact'] for e in employees_list]
        ).values_list('username', flat=True))

        # Fetch usernames of users who already have employees
        existing_employee_usernames = set(Employee.objects.filter(
            user__username__in=[e['contact'] for e in employees_list]
        ).values_list('user__username', flat=True))

        processed_contacts = set(existing_usernames)

        with transaction.atomic():
            # Create new users
            for data in employees_list:
                contact = data['contact']
                if contact in processed_contacts:
                    self.stdout.write(self.style.WARNING(
                        f"⚠️ User {contact} already exists or is duplicated. Skipping user creation."))
                    continue

                user = User(username=contact)
                user.set_password('ofankor@25')
                new_users.append(user)
                processed_contacts.add(contact)

            created_users = User.objects.bulk_create(new_users)

            # Build user mapping
            user_map = {u.username: u for u in User.objects.filter(
                username__in=[e['contact'] for e in employees_list]
            )}

            # Create employees
            for data in employees_list:
                contact = data['contact']

                if contact not in user_map:
                    continue  # Safety check

                if contact in existing_employee_usernames:
                    self.stdout.write(self.style.WARNING(
                        f"⚠️ Employee for user {contact} already exists. Skipping employee creation."))
                    continue

                employee = Employee(
                    user=user_map[contact],
                    name=data['name'],
                    gender=data['gender'],
                    contact=contact,
                    dob=data['dob'],
                    location=data['location'],
                    guarantor_name=data['guarantor_name'],
                    guarantor_contact=data['guarantor_contact'],
                    job_description=data['job_description'],
                    date_employed=data['date_employed'],
                    training_start=data['training_start'],
                    training_end=data['training_end'],
                    ssnit=data.get('ssnit', ''),
                    account=data.get('account', ''),
                    status=data.get('status', 'active'),
                    site=data['site']  # Site foreign key (pass ID in JSON)
                )
                new_employees.append(employee)

            if new_employees:
                Employee.objects.bulk_create(new_employees)

            self.stdout.write(self.style.SUCCESS(
                f"✅ Successfully created {len(new_users)} users and {len(new_employees)} employees."))
