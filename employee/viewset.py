# views.py
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from .models import (Employee, FuelSales, ShopSales, Attendance, Captain, WeeklyEvaluation, CreditSales, CreditCollection)
from .serializers import ( EmployeeSerializer, FuelSalesSerializer,
                          ShopSalesSerializer, AttendanceSerializer, CreditSalesSerializer, CaptainSerializer,
                          CreditCollectionSerializer, AttendantEvaluation, WeeklyEvaluationSerializer, 
                          AttendanceDate, BulkAttendanceSerializer)
from rest_framework.decorators import action
from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from . functions import print_model_objects, reset_model_data, convert_to_json, read_file

#reset_model_data(ShopSales)
#print_model_objects(ShopSales)

# print('hello')
#







class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]  # Basic auth - anyone logged in can access
    
    def perform_create(self, serializer):
        """Automatically link user if contact matches username"""
        contact = serializer.validated_data.get('contact')
        if self.request.user.username == contact:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's employee profile"""
        employee = Employee.objects.get(user=request.user)
        serializer = self.get_serializer(employee)
        return Response(serializer.data)
    
    
class FuelSalesViewSet(viewsets.ModelViewSet):
    queryset = FuelSales.objects.all()
    serializer_class = FuelSalesSerializer
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can post

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    

class ShopSalesViewSet(viewsets.ModelViewSet):
    queryset = ShopSales.objects.all()
    serializer_class = ShopSalesSerializer
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can post

    def perform_create(self, serializer):
        serializer.save(user=self.request.user) 
        


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can post

    def perform_create(self, serializer):
        # Get the logged-in user's employee profile
        try:
            employee = self.request.user.employee_profile
        except:
            raise PermissionDenied("No employee profile linked to this user.")

       

        if not employee.is_captain:
            raise PermissionDenied("Only Captains can mark attendance.")

        serializer.save()

    def get_queryset(self):
        # Optionally restrict captains to see today's attendance
        return Attendance.objects.filter(date=timezone.now().date())



class CreditSalesViewSet(viewsets.ModelViewSet):
    queryset = CreditSales.objects.all()
    serializer_class = CreditSalesSerializer
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can post

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        # Optional: limit to current user’s sales only
        return CreditSales.objects.all()
    
   
    
class CreditCollectionViewSet(viewsets.ModelViewSet):
    queryset = CreditCollection.objects.all()
    serializer_class = CreditCollectionSerializer
    permission_classes = [IsAuthenticated]  # Ensure only authenticated users can post

    def perform_create(self, serializer):
        # Get logged-in user's employee profile
        try:
            employee = self.request.user.employee_profile
        except:
            raise PermissionDenied("No employee profile linked to this user.")

        # Restrict to Manager and Supervisor
        if employee.job_description.lower() not in ['manager', 'supervisor']:
            raise PermissionDenied("Only Managers or Supervisors can record credit collections.")

        serializer.save()

    def get_queryset(self):
        return CreditCollection.objects.all()


class ActiveAttendantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Employee.objects.filter(status='active', job_description__in=['customer_champion', 'service_champion'])
    serializer_class = EmployeeSerializer



class CaptainViewSet(viewsets.ReadOnlyModelViewSet):  # ReadOnly since we’re only listing
    queryset = Captain.objects.all()
    serializer_class = CaptainSerializer
    


class WeeklyEvaluationViewSet(viewsets.ModelViewSet):
    queryset = WeeklyEvaluation.objects.all()
    serializer_class = WeeklyEvaluationSerializer





class WeeklyEvaluationViewSetPost(viewsets.ViewSet):
    def create(self, request):
        evaluations = request.data.get('evaluations', [])

        if not evaluations:
            return Response({'detail': 'No evaluations provided.'}, status=status.HTTP_400_BAD_REQUEST)

        today = now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Get or create the WeeklyEvaluation for this week
        weekly_evaluation, created = WeeklyEvaluation.objects.get_or_create(
            date__range=[week_start, week_end], defaults={'date': today}
        )

        created_evaluations = []

        for evaluation in evaluations:
            attendant_id = evaluation.get('attendant')
            raw_score = evaluation.get('raw_score')

            if not attendant_id or raw_score is None:
                return Response({'detail': 'Each evaluation must include attendant and raw_score.'},
                                status=status.HTTP_400_BAD_REQUEST)

            if AttendantEvaluation.objects.filter(
                weekly_evaluation=weekly_evaluation,
                attendant_id=attendant_id
            ).exists():
                return Response({'detail': f'Attendant with ID {attendant_id} has already been evaluated this week.'},
                                status=status.HTTP_400_BAD_REQUEST)

            try:
                attendant = Employee.objects.get(id=attendant_id)
            except Employee.DoesNotExist:
                return Response({'detail': f'Attendant with ID {attendant_id} does not exist.'},
                                status=status.HTTP_400_BAD_REQUEST)

            percentage_score = round((raw_score / 7) * 100, 2)

            evaluation_instance = AttendantEvaluation.objects.create(
                weekly_evaluation=weekly_evaluation,
                attendant=attendant,
                raw_score=raw_score,
                percentage_score=percentage_score
            )

            created_evaluations.append({
                'attendant': attendant.name,
                'raw_score': raw_score,
                'percentage_score': percentage_score
            })

        return Response({
            'weekly_evaluation_id': weekly_evaluation.id,
            'created': created_evaluations
        }, status=status.HTTP_201_CREATED)



class BulkAttendanceViewSet(viewsets.ModelViewSet):
    queryset = AttendanceDate.objects.all().order_by('-date')
    serializer_class = BulkAttendanceSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attendance_date = serializer.save()
        return Response({'attendance_date': str(attendance_date.date)}, status=status.HTTP_201_CREATED)