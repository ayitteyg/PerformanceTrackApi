import json
import os

from django.core.management.base import BaseCommand
from employee.models import WeeklyEvaluation  # Replace 'your_app' with your actual app name


class Command(BaseCommand):
    help = 'Load Weekly Evaluation data from JSON file into the database'

    def handle(self, *args, **kwargs):
        file_path = os.path.join('data_json', 'weekreff.json')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        with open(file_path, 'r') as file:
            try:
                weekly_data = json.load(file)
            except json.JSONDecodeError as e:
                self.stdout.write(self.style.ERROR(f'Error parsing JSON file: {e}'))
                return

        records_created = 0

        for item in weekly_data:
            date = item.get('date')

            if date:
                weekly_eval, created = WeeklyEvaluation.objects.get_or_create(date=date)

                if created:
                    records_created += 1
            else:
                self.stdout.write(self.style.WARNING(f'Missing "date" in entry: {item}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {records_created} weekly evaluation records.'))
