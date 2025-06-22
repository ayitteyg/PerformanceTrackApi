import random
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from employee.models import FuelSales, Captain, PumpTarget
from decimal import Decimal, ROUND_HALF_UP
from django.db.models import Sum
from collections import defaultdict

class Command(BaseCommand):
    help = 'OPTIMIZED: Generate fair, target-based FuelSales data for active employees (2025, 12-15 days/month)'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        PUMP_CHOICES = ['pump1', 'pump2', 'pump3', 'pump4', 'pump5']
        
        # ===== 1. Preload All Required Data =====
        with transaction.atomic():
            # Get all active employees with their related profiles
            active_employees = list(User.objects.filter(
                is_active=True,
                employee_profile__status='active'
            ).select_related('employee_profile'))
            
            if not active_employees:
                self.stdout.write(self.style.ERROR('No active employees found!'))
                return

            # Preload all captains
            captains = list(Captain.objects.all())
            captain_by_site = defaultdict(list)
            for captain in captains:
                captain_by_site[captain.site].append(captain)
            
            # Initialize pump targets (bulk create if missing)
            existing_targets = set((pt.site, pt.pump) for pt in PumpTarget.objects.all())
            new_targets = []
            
            for captain in captains:
                for pump in PUMP_CHOICES:
                    if (captain.site, pump) not in existing_targets:
                        new_targets.append(PumpTarget(
                            site=captain.site,
                            pump=pump,
                            target=Decimal(str(random.uniform(5000, 10000)))  # Convert float to Decimal
                        ))
            
            if new_targets:
                PumpTarget.objects.bulk_create(new_targets)

            # Pre-calculate total daily targets per site
            site_targets = defaultdict(Decimal)
            for pt in PumpTarget.objects.all():
                site_targets[pt.site] += Decimal(str(pt.target))  # Ensure Decimal

        # ===== 2. Prepare Data in Memory =====
        records_to_create = []
        captain_counts = defaultdict(int)
        
        for employee in active_employees:
            site = employee.employee_profile.site
            if site not in captain_by_site:
                continue
                
            # Get the least used captain for this site
            captain = min(
                captain_by_site[site],
                key=lambda c: captain_counts[c.id]
            )
            
            for month in range(1, 13):
                # Determine days in month
                if month == 2:
                    days_in_month = 28
                elif month in [4, 6, 9, 11]:
                    days_in_month = 30
                else:
                    days_in_month = 31
                
                # Select random days (12-15 per month)
                sales_days = random.sample(range(1, days_in_month + 1), k=random.randint(12, 15))
                
                for day in sales_days:
                    date = datetime(2025, month, day).date()
                    
                    pump = random.choice(PUMP_CHOICES)
                    captain_counts[captain.id] += 1
                    
                    # Calculate sales (using pre-loaded site targets)
                    total_target = site_targets[site]
                    pms_sales = (total_target * Decimal('0.68')).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP) / Decimal('12')
                    dx_sales = (total_target * Decimal('0.22')).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP) / Decimal('11')
                    vp_sales = (total_target * Decimal('0.01')).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP) / Decimal('10')
                    
                    records_to_create.append(FuelSales(
                        user=employee,
                        date=date,
                        pump=pump,
                        captain=captain,
                        pms_sales=pms_sales,
                        dx_sales=dx_sales,
                        vp_sales=vp_sales,
                    ))

        # ===== 3. Bulk Create with Conflict Handling =====
        with transaction.atomic():
            # Get existing dates per employee to avoid conflicts
            existing_records = set(FuelSales.objects.filter(
                user__in=[e.id for e in active_employees]
            ).values_list('user_id', 'date'))
            
            # Filter out duplicates
            unique_records = [
                r for r in records_to_create 
                if (r.user.id, r.date) not in existing_records
            ]
            
            # Bulk create in batches
            batch_size = 1000
            for i in range(0, len(unique_records), batch_size):
                FuelSales.objects.bulk_create(unique_records[i:i + batch_size])

        # ===== 4. Output Results =====
        self.stdout.write(self.style.SUCCESS(
            f'Created {len(unique_records)} records\n'
            f'Captains fairness:\n' +
            '\n'.join([f'- {c}: {captain_counts.get(c.id, 0)}' for c in captains])
        ))