import random
from decimal import Decimal, getcontext
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from employee.models import ShopSales, Captain, ShopTarget
from django.db.models import Q
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

class Command(BaseCommand):
    help = 'OPTIMIZED: Generate realistic ShopSales data for active employees (2025, 28-31 days/month)'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        getcontext().rounding = ROUND_HALF_UP
        
        # ===== 1. Preload All Required Data =====
        with transaction.atomic():
            # Get all active employees with their sites
            active_employees = list(User.objects.filter(
                is_active=True,
                employee_profile__status='active'
            ).select_related('employee_profile'))
            
            if not active_employees:
                self.stdout.write(self.style.ERROR('No active employees found!'))
                return

            # Preload all service champion captains with their sites
            captains = list(Captain.objects.filter(
                Q(user__employee_profile__job_description__iexact='service_champion')
            ))
            captain_by_site = defaultdict(list)
            for captain in captains:
                captain_by_site[captain.site].append(captain)
            
            # Initialize shop targets (bulk create if missing)
            existing_sites = set(ShopTarget.objects.values_list('site', flat=True))
            new_targets = []
            
            for site in {c.site for c in captains}:
                if site not in existing_sites:
                    new_targets.append(ShopTarget(
                        site=site,
                        target=Decimal('13000')
                    ))
            
            if new_targets:
                ShopTarget.objects.bulk_create(new_targets)

            # Pre-load all shop targets
            site_targets = {st.site: st.target for st in ShopTarget.objects.all()}

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

                # Select random days (up to the number of days in the month)
                max_possible_days = min(days_in_month, 30)  # You can't pick more than the days in the month
                sales_days = random.sample(range(1, days_in_month + 1), k=random.randint(28, max_possible_days))
                
                for day in sales_days:
                    date = datetime(2025, month, day).date()
                    
                    # Skip if record exists (we'll check in bulk later)
                    captain_counts[captain.id] += 1
                    
                    # Get target for this site (with fallback)
                    daily_target = site_targets.get(site, Decimal('13000'))
                    
                    # Generate random factor as Decimal first
                    random_factor = Decimal(str(random.uniform(0.8, 1.2)))
                    base_sales = (Decimal(str(daily_target)) * random_factor).quantize(Decimal('0.00'))
                    
                    # Apply day-of-week variations (convert random to Decimal first)
                    if date.weekday() in [5, 6]:  # Weekend
                        weekend_factor = Decimal(str(random.uniform(1.2, 1.5)))
                        base_sales *= weekend_factor
                    else:
                        weekday_factor = Decimal(str(random.uniform(0.9, 1.1)))
                        base_sales *= weekday_factor
                    
                    sales_value = base_sales.quantize(Decimal('0.00'))
                    
                    records_to_create.append(ShopSales(
                        user=employee,
                        date=date,
                        captain=captain,
                        sales=sales_value,
                    ))

        # ===== 3. Bulk Create with Conflict Handling =====
        with transaction.atomic():
            # Get existing dates per employee to avoid conflicts
            existing_records = set(ShopSales.objects.filter(
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
                ShopSales.objects.bulk_create(unique_records[i:i + batch_size])

        # ===== 4. Output Results =====
        self.stdout.write(self.style.SUCCESS(
            f'Created {len(unique_records)} ShopSales records\n'
            f'Captains fairness:\n' +
            '\n'.join([f'- {c}: {captain_counts.get(c.id, 0)}' for c in captains])
        ))