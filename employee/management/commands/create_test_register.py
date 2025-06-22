import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from employee.models import AttendanceDate, AttendanceRegister, Employee

class Command(BaseCommand):
    help = 'Generate bulk attendance/punctuality data for employees'

    def handle(self, *args, **kwargs):
        employees = Employee.objects.filter(status='active')

        if not employees.exists():
            self.stdout.write(self.style.ERROR('No active employees found!'))
            return

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)

        records_created = 0
        current_date = start_date

        with transaction.atomic():
            while current_date <= end_date:
                # Create or get attendance date
                attendance_date, _ = AttendanceDate.objects.get_or_create(date=current_date)

                attendance_records = []

                for employee in employees:
                    # Generate random score with realistic distribution
                    rand = random.random()
                    if rand < 0.85:
                        raw_score = 2.0
                    elif rand < 0.95:
                        raw_score = round(random.uniform(1.5, 1.9), 1)
                    else:
                        raw_score = round(random.uniform(0.1, 1.4), 1)

                    attendance_records.append(
                        AttendanceRegister(
                            attendance_date=attendance_date,
                            attendant=employee,
                            raw_score=raw_score
                        )
                    )

                # Bulk insert for this day
                AttendanceRegister.objects.bulk_create(attendance_records, batch_size=1000)

                records_created += len(attendance_records)
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
