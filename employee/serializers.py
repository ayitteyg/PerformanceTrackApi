# serializers.py
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta, date
from .models import (Employee, FuelSales, CreditSales, CreditCollection, AttendanceDate, AttendanceRegister,
                     ShopSales, Attendance, Captain, AttendantEvaluation, WeeklyEvaluation)



class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'
        read_only_fields = ('user',)  # User is set automatically

    def validate_contact(self, value):
        """Basic contact validation"""
        if not value.isdigit():
            raise serializers.ValidationError("Contact must contain only numbers")
        return value


class FuelSalesSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='user.employee_profile.name', read_only=True)
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    captain_name = serializers.SerializerMethodField()  # 👈 Add this line

    class Meta:
        model = FuelSales
        fields = '__all__'  # Or list specific fields if you want more control
        
    def get_captain_name(self, obj):
        return obj.captain.user.employee_profile.name # 👈 This will return the captain's name


class ShopSalesSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='user.employee_profile.name', read_only=True)
    captain_name = serializers.SerializerMethodField()  # 👈 Add this line


    class Meta:
        model = ShopSales
        fields = '__all__'
    
    def get_captain_name(self, obj):
        return obj.captain.user.employee_profile.name  # 👈 This will return the captain's name



class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = '__all__'

    def validate(self, data):
        from django.utils import timezone

        # Prevent marking for past or future dates
        if data['date'] != timezone.now().date():
            raise serializers.ValidationError("You can only mark attendance for today.")

        return data
    


class AttendantEvaluationInputSerializer(serializers.Serializer):
    attendant = serializers.IntegerField()
    raw_score = serializers.FloatField()

    def validate_raw_score(self, value):
        if value > 7.0:
            raise serializers.ValidationError('Score cannot exceed 7.0.')
        return value


class CreditSalesSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = CreditSales
        fields = '__all__'


class CreditCollectionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = CreditCollection
        fields = '__all__'


class CaptainSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.employee_profile.name', read_only=True)

    class Meta:
        model = Captain
        fields = ['id', 'name']
        


class AttendantEvaluationInputSerializer(serializers.Serializer):
    attendant = serializers.IntegerField()
    raw_score = serializers.FloatField()

    def validate_raw_score(self, value):
        if value > 7.0:
            raise serializers.ValidationError('Score cannot exceed 7.0.')
        return value

    def validate_attendant(self, value):
        try:
            employee = Employee.objects.get(id=value)
        except Employee.DoesNotExist:
            raise serializers.ValidationError('Attendant does not exist.')

        if employee.job_description.lower() not in ['customer_champion', 'service_champion']:
            raise serializers.ValidationError('Only Customer Champion or Service Champion can be evaluated.')

        if employee.status.lower() != 'active':
            raise serializers.ValidationError('Only active attendants can be evaluated.')

        return value


class AttendantEvaluationSerializer(serializers.ModelSerializer):
    attendant_name = serializers.CharField(source='attendant.name', read_only=True)

    class Meta:
        model = AttendantEvaluation
        fields = ['id', 'attendant', 'attendant_name', 'raw_score', 'percentage_score']


class WeeklyEvaluationSerializer(serializers.Serializer):
    # evaluations = AttendantEvaluationInputSerializer(many=True)
    evaluations = AttendantEvaluationSerializer(source='attendant_scores', many=True, read_only=True)

    def create(self, validated_data):
        from datetime import date

        evaluations_data = validated_data.pop('evaluations')

        # Automatically determine the current week
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Check if a WeeklyEvaluation already exists for this week
        weekly_evaluation = WeeklyEvaluation.objects.filter(date__range=[week_start, week_end]).first()
        if not weekly_evaluation:
            weekly_evaluation = WeeklyEvaluation.objects.create()

        for evaluation in evaluations_data:
            attendant_id = evaluation['attendant']
            raw_score = evaluation['raw_score']

            # Check if this attendant is already evaluated this week
            if AttendantEvaluation.objects.filter(
                weekly_evaluation=weekly_evaluation,
                attendant_id=attendant_id
            ).exists():
                raise serializers.ValidationError(f'Attendant with ID {attendant_id} has already been evaluated this week.')

            # Create the attendant evaluation
            AttendantEvaluation.objects.create(
                weekly_evaluation=weekly_evaluation,
                attendant_id=attendant_id,
                raw_score=raw_score,
                percentage_score=round((raw_score / 7) * 100, 2)
            )

        return weekly_evaluation






class AttendanceInputSerializer(serializers.Serializer):
    attendant = serializers.IntegerField()
    raw_score = serializers.FloatField()

    def validate_raw_score(self, value):
        if value > 2.0:
            raise serializers.ValidationError('Score cannot exceed 2.0.')
        return value


class AttendanceRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRegister
        fields = ['attendant', 'raw_score', 'percentage_mark']


class BulkAttendanceSerializer(serializers.Serializer):
    register = AttendanceInputSerializer(many=True)

    def create(self, validated_data):
        attendances_data = validated_data.pop('register')

        # Automatically determine today's attendance date
        today = date.today()
        attendance_date, created = AttendanceDate.objects.get_or_create(date=today)

        for attendance in attendances_data:
            attendant_id = attendance['attendant']
            raw_score = attendance['raw_score']

            # Prevent duplicate marking
            if AttendanceRegister.objects.filter(
                attendance_date=attendance_date,
                attendant_id=attendant_id
            ).exists():
                raise serializers.ValidationError(f'Attendant with ID {attendant_id} has already been marked for today.')

            AttendanceRegister.objects.create(
                attendance_date=attendance_date,
                attendant_id=attendant_id,
                raw_score=raw_score,
                percentage_mark=round((raw_score / 2) * 100, 2)
            )

        return attendance_date