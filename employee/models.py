
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.contrib.auth import get_user_model  # Add this import at the top
from django.utils import timezone
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction


class CustomUser(AbstractUser):
    is_captain = models.BooleanField(default=False)
    is_manager = models.BooleanField(default=False)
    is_supervisor = models.BooleanField(default=False)
    is_noRole = models.BooleanField(default=True)

    def __str__(self):
        return self.username






PUMP_CHOICES = [
        ('pump1', 'Pump 1'),
        ('pump2', 'Pump 2'),
        ('pump3', 'Pump 3'),
        ('pump4', 'Pump 4'),
        ('pump5', 'Pump 5'),
    ]

JOB_DESCRIPTION_CHOICES = [
    ('manager', 'Manager'),
    ('supervisor', 'Supervisor'),
    ('quality_marshal', 'Quality Marshal'),
    ('customer_champion', 'Customer Champion'),
    ('service_champion', 'Service Champion'),
    ('lube_technician', 'Lube Technician'),
    ('oil_specialist', 'Oil Specialist'),
    ('cleaner', 'Cleaner'),
    ('security', 'Security'),
    ('driver', 'Driver'),
]


SITE_CHOICES = [
        ('ofankor', 'Ofankor'),
        ('palmwine', 'Palmwine'),
        ('eastlegon', 'East Legon'),
        ('achimota_ksi', 'Achimota KSI'),
        ('achimota_abofu', 'Achimota Abofu'),
        ('bohye', 'Bohye'),
        ('airport', 'Airport'),
    ]


STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
    ]

GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]





class Employee(models.Model):
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile',
        null=True,
        blank=True  # Recommended to add this
    )

    name = models.CharField(max_length=100)
    gender = models.CharField(choices=GENDER_CHOICES, max_length=6)
    contact = models.CharField(max_length=20)
    dob = models.DateField(verbose_name="Date of Birth")
    location = models.CharField(max_length=200)
    guarantor_name = models.CharField(max_length=100)
    guarantor_contact = models.CharField(max_length=20)
    job_description = models.CharField(max_length=50, choices=JOB_DESCRIPTION_CHOICES)
    date_employed = models.DateField()
    training_start = models.DateField()
    training_end = models.DateField()
    ssnit = models.CharField(max_length=20, default="", null=True, blank=True)
    account = models.CharField(max_length=20, default="", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    site = models.CharField(max_length=15, choices=SITE_CHOICES)
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """
        Automatically link user account if username matches the employee's contact.
        """
        User = get_user_model()  # Get the actual User model class
        if not self.user_id:  # Only if user isn't already assigned
            try:
                self.user = User.objects.get(username=self.contact)
            except User.DoesNotExist:
                pass  # Or handle the case where user doesn't exist
        super().save(*args, **kwargs)


#captain model
class Captain(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default="", null=True, blank=True)
    site = models.CharField(max_length=15, choices=SITE_CHOICES)

    def __str__(self):
        return self.user.username  # or self.user.get_full_name() if you have full name


#fuelsales
class FuelSales(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    pump = models.CharField(max_length=10, choices=PUMP_CHOICES)
    captain = models.ForeignKey(Captain, on_delete=models.CASCADE, related_name='fuel_sales')
    pms_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    dx_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    vp_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    performance = models.DecimalField(
        max_digits=5,          # Allows up to 999.99%
        decimal_places=2,      # Two decimal places
        null=True,
        blank=True,
        editable=False
    )
    

    @property
    def total_sales(self):
        return self.pms_sales + self.dx_sales + self.vp_sales
    
    @property
    def employee_name_and_total_sales(self):
        return f'{self.user.employee_profile.name} - Total Sales: {self.total_sales}'

    def calculate_performance(self):
        """Calculate and return the performance percentage with proper rounding"""
        try:
            site = self.user.employee_profile.site
            pump_target = PumpTarget.objects.get(site=site, pump=self.pump)
            if pump_target.target > 0:
                performance = (Decimal(self.total_sales) / Decimal(pump_target.target)) * 100
                return performance.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
            return Decimal('0.00')
        except (PumpTarget.DoesNotExist, AttributeError):
            return None


    def save(self, *args, **kwargs):
        """Override save to calculate performance before saving"""
        self.performance = self.calculate_performance()
        super().save(*args, **kwargs)
        
        
    #for batch updating
    @transaction.atomic
    def update_existing_performances():
        for fuel_sale in FuelSales.objects.all():
            fuel_sale.save()  # This will trigger the performance calculation

    def __str__(self):
        return f'{self.date} - {self.pump}'


#shop sales
class ShopSales(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    captain = models.ForeignKey('Captain', on_delete=models.CASCADE, related_name='shop_sales')
    sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    performance = models.DecimalField(
        max_digits=5,          # Allows up to 999.99%
        decimal_places=2,      # Two decimal places
        null=True,
        blank=True,
        editable=False
    )
    
    class Meta:
        unique_together = ('user', 'date')

    @property
    def total_sales(self):
        return self.sales

    
    def calculate_performance(self):
        """Calculate and return the performance percentage with proper rounding"""
        try:
            site = self.user.employee_profile.site
            shop_target = ShopTarget.objects.get(site=site)
            if shop_target.target > 0:
                performance = (Decimal(self.total_sales) / Decimal(shop_target.target)) * 100
                return performance.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
            return Decimal('0.00')
        except (ShopTarget.DoesNotExist, AttributeError):
            return None
    
    
    def save(self, *args, **kwargs):
        """Override save to calculate performance before saving"""
        self.performance = self.calculate_performance()
        super().save(*args, **kwargs)
        
        
     #for batch updating
    @transaction.atomic
    def update_existing_performances():
        for shop_sale in ShopSales.objects.all():
            shop_sale.save()  # This will trigger the performance calculation

    def __str__(self):
        return f'{self.date} - {self.pump}'
    
    def __str__(self):
        return f'{self.user.employee_profile.name} - Sales: {self.total_sales}'
     


#shop target
class ShopTarget(models.Model):
    site =  models.CharField(max_length=15, choices=SITE_CHOICES)
    target = models.FloatField()

    def __str__(self):
        return f'{self.target}'



#pump target
class PumpTarget(models.Model):
    site =  models.CharField(max_length=15, choices=SITE_CHOICES)
    pump = models.CharField(max_length=10, choices=PUMP_CHOICES)
    target = models.FloatField()

    def __str__(self):
        return f'{self.pump} Target: {self.target}'



#AttendanceRegister
class Attendance(models.Model):
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
        ('off', 'Off Day'),
    ]

    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default='present')

    class Meta:
        unique_together = ('employee', 'date')  # No duplicate markings

    def __str__(self):
        return f'{self.employee.name} - {self.date} - {self.status}'




class WeeklyEvaluation(models.Model):
    date = models.DateField(default=now)

    @property
    def week_number(self):
        return self.date.isocalendar()[1]  # ISO week number

    def __str__(self):
        return f'Evaluation for Week {self.week_number}, {self.date.year}'


# Attendant Evaluation
class AttendantEvaluation(models.Model):
    weekly_evaluation = models.ForeignKey(WeeklyEvaluation, on_delete=models.CASCADE, related_name='attendant_scores')
    attendant = models.ForeignKey('Employee', on_delete=models.CASCADE)
    raw_score = models.FloatField()
    percentage_score = models.FloatField(blank=True, null=True)

    def clean(self):
        if self.raw_score > 7.0:
            raise ValidationError('Score cannot exceed 7.0.')

        if self.attendant.job_description.lower() not in ['customer_champion', 'service_champion']:
            raise ValidationError('Only Customer Champion or Service Champion can be evaluated.')

    def save(self, *args, **kwargs):
        self.percentage_score = round((self.raw_score / 7) * 100, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.attendant.name} - {self.percentage_score}% on {self.weekly_evaluation.date}'




#credit customers
class Customer(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)

    def __str__(self):
        return self.name
    

class CreditSales(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_sales')
    date = models.DateField(auto_now_add=True)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='credit_sales')
    car_number = models.CharField(max_length=20)
    litres = models.FloatField(null=True, blank=True)
    amount = models.FloatField()

    def __str__(self):
        return f'{self.customer.name} - {self.amount}'
    

class CreditCollection(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='credit_collections')
    date = models.DateField(auto_now_add=True)
    amount = models.FloatField()

    def __str__(self):
        return f'{self.customer.name} - {self.amount} on {self.date}'




class AttendanceDate(models.Model):
    date = models.DateField(default=now, unique=True)

    def __str__(self):
        return f'Attendance for {self.date}'



class AttendanceRegister(models.Model):
    attendance_date = models.ForeignKey(AttendanceDate, on_delete=models.CASCADE, related_name='attendance_mark')
    attendant = models.ForeignKey('Employee', on_delete=models.CASCADE)
    raw_score = models.FloatField()
    percentage_mark = models.FloatField(blank=True, null=True)

    def clean(self):
        if self.raw_score > 2.0:
            raise ValidationError('Score cannot exceed 2.0.')

    def save(self, *args, **kwargs):
        self.percentage_mark = round((self.raw_score / 2) * 100, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.attendant.name} - {self.percentage_mark}% on {self.attendance_date.date}'