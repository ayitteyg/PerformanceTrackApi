import random
from decimal import Decimal
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from employee.models import FuelSales, Captain, PumpTarget, Employee
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum

class Command(BaseCommand):
    help = 'Generate fair, target-based FuelSales data for active employees (2025, 12-15 days/month)'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        
        PUMP_CHOICES = [
        ('pump1', 'Pump 1'),
        ('pump2', 'Pump 2'),
        ('pump3', 'Pump 3'),
        ('pump4', 'Pump 4'),
        ('pump5', 'Pump 5'),
    ]
        
        # ===== 1. Only Active Employees =====
        active_employees = User.objects.filter(
            is_active=True,
            employee_profile__status='active'
        ).select_related('employee_profile')
        
        if not active_employees.exists():
            self.stdout.write(self.style.ERROR('No active employees found!'))
            return

        # ===== 2. Date Range (2025 only) =====
        start_date = datetime(2025, 1, 1).date()
        end_date = datetime(2025, 12, 31).date()

        # ===== 3. Prepare Pump Targets =====
        pumps = [choice[0] for choice in PUMP_CHOICES]
        captains = Captain.objects.all()
        
        # Ensure all captains have PumpTargets
        for captain in captains:
            for pump in pumps:
                PumpTarget.objects.get_or_create(
                    site=captain.site,
                    pump=pump,
                    defaults={'target': Decimal(random.uniform(5000, 10000))}
                )

        # ===== 4. Generate Data =====
        records_created = 0
        captain_records = {captain.id: 0 for captain in captains}

        for employee in active_employees:
            for month in range(1, 13):
                # Randomly pick 12-15 days/month
                days_in_month = 30 if month in [4, 6, 9, 11] else 31
                days_in_month = 28 if month == 2 else days_in_month
                sales_days = sorted(random.sample(
                    range(1, days_in_month + 1),
                    k=random.randint(12, 15)
                ))

                for day in sales_days:
                    date = datetime(2025, month, day).date()
                    
                    if FuelSales.objects.filter(date=date, user=employee).exists():
                        continue

                    # Choose pump and captain (fair distribution)
                    pump = random.choice(pumps)
                    captain = min(
                        captains.filter(site=employee.employee_profile.site),
                        key=lambda c: captain_records[c.id]
                    )
                    captain_records[captain.id] += 1

                                        # Get sum of all pump targets for this site (total_daily_target)
                                        
                    # Get sum of all pump targets for this site (total_daily_target)
                    total_daily_target = PumpTarget.objects.filter(
                        site=captain.site
                    ).aggregate(total=Sum('target'))['total'] or 0.0

                    # Ensure total_daily_target is a Decimal
                    total_daily_target = Decimal(str(total_daily_target))

                    # Generate sales based on fixed percentages of total daily target
                    pms_sales = (total_daily_target * Decimal('0.68')).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)/12
                    dx_sales = (total_daily_target * Decimal('0.22')).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)/11
                    vp_sales = (total_daily_target * Decimal('0.01')).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)/10
                    
                    # pms_sales=Decimal(random.uniform(800, 1600)).quantize(Decimal('0.00')),
                    # dx_sales=Decimal(random.uniform(500, 1000)).quantize(Decimal('0.00')),
                    # vp_sales=Decimal(random.uniform(200, 500)).quantize(Decimal('0.00')),

                                        
                    
                    with transaction.atomic():
                        FuelSales.objects.create(
                            user=employee,
                            date=date,
                            pump=pump,
                            captain=captain,
                            pms_sales=pms_sales,
                            dx_sales=dx_sales,
                            vp_sales=vp_sales,
                        )
                        records_created += 1

        # ===== 5. Output Results =====
        self.stdout.write(self.style.SUCCESS(
            f'Created {records_created} records\n'
            f'Captains fairness:\n' +
            '\n'.join([f'- {c}: {captain_records[c.id]}' for c in captains])
        ))