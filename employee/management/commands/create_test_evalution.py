import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from employee.models import WeeklyEvaluation, AttendantEvaluation, Employee

class Command(BaseCommand):
    help = 'Generate bulk weekly evaluation data for attendants'

    def handle(self, *args, **kwargs):
        # 1. Get all eligible attendants (Customer Champions and Service Champions)
        attendants = Employee.objects.filter(
            job_description__in=['customer_champion', 'service_champion'],
            status='active'
        )
        
        print('loading started...')
        
        if not attendants.exists():
            self.stdout.write(self.style.ERROR('No eligible attendants found!'))
            print("No attendants found")
            return

        # 2. Set date range (last 12 months)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=365)
        
        # 3. Generate weekly evaluations
        records_created = 0
        current_date = start_date
        
        with transaction.atomic():
            while current_date <= end_date:
                # Create weekly evaluation (Mondays only)
                if current_date.weekday() == 0:  # Monday
                    weekly_eval, created = WeeklyEvaluation.objects.get_or_create(
                        date=current_date
                    )
                    
                    if created:
                        # Evaluate each attendant for this week
                        for attendant in attendants:
                            # Generate random score (4.0-7.0 range, most in 5.0-6.5)
                            raw_score = random.uniform(4.0, 7.0)
                            if random.random() > 0.2:  # 80% chance to be in 5.0-6.5
                                raw_score = random.uniform(5.0, 6.5)
                            
                            AttendantEvaluation.objects.create(
                                weekly_evaluation=weekly_eval,
                                attendant=attendant,
                                raw_score=round(raw_score, 1)  # Round to 1 decimal
                            )
                            records_created += 1
                
                current_date += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {records_created} evaluation records\n'
            f'Covering {attendants.count()} attendants from '
            f'{start_date} to {end_date}\n'
            f'Score distribution:\n'
            '- 80% between 5.0-6.5\n'
            '- 20% between 4.0-7.0'
        ))