import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from employee.models import AttendanceDate, AttendanceRegister, Employee

class Command(BaseCommand):
    help = 'Generate bulk attendance/punctuality data for employees'

    def handle(self, *args, **kwargs):
        # 1. Get all active employees
        employees = Employee.objects.filter(status='active')
        
        if not employees.exists():
            self.stdout.write(self.style.ERROR('No active employees found!'))
            return

        # 2. Set date range (last 3 months)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)
        
        # 3. Generate daily attendance records
        records_created = 0
        current_date = start_date
        
        with transaction.atomic():
            while current_date <= end_date:
                # Create attendance date record
                attendance_date, created = AttendanceDate.objects.get_or_create(
                    date=current_date
                )
                
                if created:
                    # Create attendance record for each employee
                    for employee in employees:
                        # Generate random score with realistic distribution
                        if random.random() < 0.85:  # 85% chance of perfect attendance
                            raw_score = 2.0
                        elif random.random() < 0.1:  # 10% chance of minor lateness
                            raw_score = round(random.uniform(1.5, 1.9), 1)
                        else:  # 5% chance of significant lateness/absence
                            raw_score = round(random.uniform(0.1, 1.4), 1)
                        
                        AttendanceRegister.objects.create(
                            attendance_date=attendance_date,
                            attendant=employee,
                            raw_score=raw_score
                        )
                        records_created += 1
                
                current_date += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {records_created} attendance records\n'
            f'Covering {employees.count()} employees from '
            f'{start_date} to {end_date}\n'
            f'Score distribution:\n'
            '- 85% perfect attendance (2.0)\n'
            '- 10% minor lateness (1.5-1.9)\n'
            '- 5% significant lateness/absence (0.1-1.4)'
        ))