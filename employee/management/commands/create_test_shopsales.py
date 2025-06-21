import random
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from employee.models import ShopSales, Captain, ShopTarget, Employee
from django.db.models import Q
from decimal import Decimal, ROUND_HALF_UP

class Command(BaseCommand):
    help = 'Generate realistic ShopSales data for active employees (2025, 12-15 days/month)'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        
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

        # ===== 3. Prepare Shop Targets =====
        captains = Captain.objects.filter(
            Q(user__employee_profile__job_description__iexact='service_champion') 
        )
        
        # Ensure all sites have ShopTargets
        sites = set(captain.site for captain in captains)
        for site in sites:
            ShopTarget.objects.get_or_create(
                site=site,
                defaults={'target': Decimal(13000)}
            )

        # ===== 4. Generate Data =====
        records_created = 0
        captain_records = {captain.id: 0 for captain in captains}

        for employee in active_employees[:1]:
            for month in range(1, 13):
                # Randomly pick 12-15 days/month
                days_in_month = 30 if month in [4, 6, 9, 11] else 31
                days_in_month = 28 if month == 2 else days_in_month
                sales_days = sorted(random.sample(
                    range(1, days_in_month + 1),
                    k=random.randint(28, 31)
                ))

                for day in sales_days:
                    date = datetime(2025, month, day).date()
                    
                    if ShopSales.objects.filter(date=date, user=employee).exists():
                        continue

                    # Choose captain (fair distribution)
                    captain = min(
                        captains.filter(site=employee.employee_profile.site),
                        key=lambda c: captain_records[c.id]
                    )
                    captain_records[captain.id] += 1

                    # Get shop target for this site
                    try:
                        shop_target = ShopTarget.objects.get(site=employee.employee_profile.site)
                        daily_target = shop_target.target 
                    except ShopTarget.DoesNotExist:
                        daily_target = Decimal('13000')  # Fallback value

                    # Generate sales with some variance around the target
                 
                    base_sales = (Decimal(str(daily_target)) * Decimal(str(random.uniform(0.8, 1.2)))).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

                    
                    # Apply day-of-week variations (weekends higher)
                    if date.weekday() in [5, 6]:  # Saturday/Sunday
                        base_sales *= Decimal(random.uniform(1.2, 1.5))
                    else:
                        base_sales *= Decimal(random.uniform(0.9, 1.1))

                    sales_value = base_sales.quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                    
                    with transaction.atomic():
                        ShopSales.objects.create(
                            user=employee,
                            date=date,
                            captain=captain,
                            sales=sales_value,
                        )
                        records_created += 1

        # ===== 5. Output Results =====
        self.stdout.write(self.style.SUCCESS(
            f'Created {records_created} ShopSales records\n'
            f'Captains fairness:\n' +
            '\n'.join([f'- {c}: {captain_records[c.id]}' for c in captains])
        ))