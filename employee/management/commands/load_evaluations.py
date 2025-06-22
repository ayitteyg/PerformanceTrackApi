import json
import os

from django.core.management.base import BaseCommand
from django.db import transaction
from employee.models import AttendantEvaluation, WeeklyEvaluation, Employee  # Replace 'your_app' with your actual app name

class Command(BaseCommand):
    help = 'Load Attendant Evaluation data from JSON file into the database'

    def handle(self, *args, **kwargs):
        file_path = os.path.join('data_json', 'evaluations.json')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        with open(file_path, 'r') as file:
            try:
                evaluations = json.load(file)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'Error parsing JSON file: {e}'))
                return

        records_created = 0

        with transaction.atomic():
            for item in evaluations:
                weekly_evaluation_id = item.get('weekly_evaluation_id')
                attendant_id = item.get('attendant_id')
                raw_score = item.get('raw_score')
                percentage_score = item.get('percentage_score')

                try:
                    weekly_evaluation = WeeklyEvaluation.objects.get(id=weekly_evaluation_id)
                    attendant = Employee.objects.get(id=attendant_id)

                    AttendantEvaluation.objects.create(
                        weekly_evaluation=weekly_evaluation,
                        attendant=attendant,
                        raw_score=raw_score,
                        percentage_score=percentage_score
                    )
                    records_created += 1

                except WeeklyEvaluation.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'WeeklyEvaluation ID {weekly_evaluation_id} not found. Skipping.'))
                except Employee.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'Attendant ID {attendant_id} not found. Skipping.'))

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {records_created} evaluation records.'))
