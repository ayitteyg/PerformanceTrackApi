from django.db.models import Avg, Q, Sum
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from . models import FuelSales, ShopSales, AttendantEvaluation, AttendanceRegister
from rest_framework.permissions import IsAuthenticated
from datetime import date
from django.utils.timezone import now
from calendar import monthrange
from decimal import Decimal
from django.contrib.auth import get_user_model
from .models import FuelSales, PumpTarget, Captain, ShopTarget




User = get_user_model()

class CombinedPerformanceView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id=None):
        if not user_id:
            user_id = request.user.id
        
        # Get query parameters with defaults
        year = int(request.query_params.get('year', datetime.now().year))
        last_n_days = int(request.query_params.get('last_n_days', 30))

        # ===== 1. Fuel Performance Data =====
        # Average performance
        avg_performance = FuelSales.objects.filter(user_id=user_id).aggregate(
            avg_performance=Avg('performance')
        )['avg_performance'] or 0

        # Quarterly breakdown
        quarters = []
        for quarter in range(1, 5):
            start_month = 3 * quarter - 2
            end_month = 3 * quarter
            quarterly_avg = FuelSales.objects.filter(
                Q(user_id=user_id) & 
                Q(date__year=year) &
                Q(date__month__gte=start_month) & 
                Q(date__month__lte=end_month)
            ).aggregate(avg=Avg('performance'))['avg'] or 0
            quarters.append({
                'quarter': f'Q{quarter}',
                'average': round(float(quarterly_avg), 2)
            })

        # Monthly data
        monthly_data = [
            {
                'month': datetime(year, item['date__month'], 1).strftime('%b'),
                'performance': round(float(item['avg_performance'] or 0), 2)
            }
            for item in FuelSales.objects.filter(
                user_id=user_id,
                date__year=year
            ).values('date__month').annotate(
                avg_performance=Avg('performance')
            ).order_by('date__month')
        ]

        # Daily data (last N days)
        date_threshold = datetime.now() - timedelta(days=last_n_days)
        daily_data = [
            {
                'date': item['date'].strftime('%Y-%m-%d'),
                'day': item['date'].strftime('%a'),
                'performance': round(float(item['performance'] or 0), 2)
            }
            for item in FuelSales.objects.filter(
                user_id=user_id,
                date__year=year,
                date__gte=date_threshold
            ).values('date').annotate(
                performance=Avg('performance')
            ).order_by('date')
        ]

        # ===== 2. Evaluation Data =====
        evaluations = AttendantEvaluation.objects.filter(
            attendant=user_id
        ).order_by('-weekly_evaluation__date')[:10]  # Last 10 evaluations

        average_score = round(
            sum(e.percentage_score for e in evaluations) / evaluations.count(), 2
        ) if evaluations.exists() else 0.0

        performance_history = [
            {
                'date': eval.weekly_evaluation.date.strftime('%Y-%m-%d'),
                'performance': eval.percentage_score
            }
            for eval in evaluations
        ]

        # ===== 3. Final Response =====
        return Response({
            # Core metrics
            'average_performance': round(float(avg_performance), 2),
            'average_score': average_score,
            
            # Time-based data
            'quarterly_performance': quarters,
            'monthly_performance': monthly_data,
            'daily_performance': daily_data,
            'performance_history': performance_history,
            
            # Metadata
            'meta': {
                'year': year,
                'last_n_days': last_n_days,
                'current_quarter': f"Q{(datetime.now().month-1)//3 + 1}",
                'generated_at': datetime.now().isoformat()
            }
        }, status=status.HTTP_200_OK)        
        


class UserPerformanceSummaryFuel(APIView):
    def get(self, request, user_id=None):
        if not user_id:
            user_id = 3 #request.user.id
        
        # Get optional query parameters
        year = int(request.query_params.get('year', datetime.now().year))
        last_n_days = int(request.query_params.get('last_n_days', 30))  # Default 30 days

        # 1. Average performance for the user
        avg_performance = FuelSales.objects.filter(user_id=user_id).aggregate(
            avg_performance=Avg('performance')
        )['avg_performance'] or 0

        # 2. Quarterly performance breakdown
        quarters = []
        for quarter in range(1, 5):
            start_month = 3 * quarter - 2
            end_month = 3 * quarter
            q_filter = Q(user_id=user_id) & Q(
                date__year=year,
                date__month__gte=start_month,
                date__month__lte=end_month
            )
            quarterly_avg = FuelSales.objects.filter(q_filter).aggregate(
                avg=Avg('performance')
            )['avg'] or 0
            quarters.append({
                'quarter': f'Q{quarter}',
                'average': round(float(quarterly_avg), 2)
            })

        # 3. Monthly performance for graphing
        monthly_performance = FuelSales.objects.filter(
            user_id=user_id,
            date__year=year
        ).values('date__month').annotate(
            avg_performance=Avg('performance')
        ).order_by('date__month')

        monthly_data = [{
            'month': datetime(year, item['date__month'], 1).strftime('%b'),
            'performance': round(float(item['avg_performance'] or 0), 2)
        } for item in monthly_performance]
  
         # Calculate the date threshold
        date_threshold = datetime.now() - timedelta(days=last_n_days)

        # Filter by year and last N days
        daily_performance = FuelSales.objects.filter(
            user_id=user_id,
            date__year=year,                # Filter by selected year
            # date__gte=date_threshold        # Additionally filter by date range
        ).values('date').annotate(
            performance=Avg('performance')  # Or any relevant field
        ).order_by('date')

        daily_data = [{
            'date': item['date'].strftime('%Y-%m-%d'),
            'day': item['date'].strftime('%a'),  # Short day name (Mon, Tue, etc.)
            'performance': round(float(item['performance'] or 0), 2)
        } for item in daily_performance]

        return Response({
            'average_performance': round(float(avg_performance), 2),
            'quarterly_performance': quarters,
            'monthly_performance': monthly_data,
            'daily_performance': daily_data,  # NEW
            'meta': {
                'year': year,
                'last_n_days': last_n_days
            }
        }, status=status.HTTP_200_OK)


class EvaluationSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        if not user_id:
            user_id = request.user.id

        # Get current date and determine current quarter
        today = date.today()
        current_month = today.month

        if current_month in [1, 2, 3]:
            quarter_start = date(today.year, 1, 1)
            quarter_end = date(today.year, 3, 31)
        elif current_month in [4, 5, 6]:
            quarter_start = date(today.year, 4, 1)
            quarter_end = date(today.year, 6, 30)
        elif current_month in [7, 8, 9]:
            quarter_start = date(today.year, 7, 1)
            quarter_end = date(today.year, 9, 30)
        else:
            quarter_start = date(today.year, 10, 1)
            quarter_end = date(today.year, 12, 31)

        # Fetch evaluations for this user in the current quarter
        evaluations = AttendantEvaluation.objects.filter(
            attendant=user_id,
            weekly_evaluation__date__range=[quarter_start, quarter_end]
        ).order_by('-weekly_evaluation__date')

        # Calculate average score
        if evaluations.exists():
            total_score = sum([e.percentage_score for e in evaluations])
            average_score = round(total_score / evaluations.count(), 2)
        else:
            average_score = 0.0

        # Get last 10 evaluations
        last_10 = evaluations[:10]
        performance_history = [
            {'date': eval.weekly_evaluation.date, 'score': eval.percentage_score}
            for eval in last_10
        ]

        return Response({
            'qtr_score': average_score,
            'score_history': performance_history
        })
        
        
class AttendanceSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        if not user_id:
            user_id = request.user.id

        # Determine current quarter
        today = date.today()
        current_month = today.month

        if current_month in [1, 2, 3]:
            quarter_start = date(today.year, 1, 1)
            quarter_end = date(today.year, 3, 31)
        elif current_month in [4, 5, 6]:
            quarter_start = date(today.year, 4, 1)
            quarter_end = date(today.year, 6, 30)
        elif current_month in [7, 8, 9]:
            quarter_start = date(today.year, 7, 1)
            quarter_end = date(today.year, 9, 30)
        else:
            quarter_start = date(today.year, 10, 1)
            quarter_end = date(today.year, 12, 31)

        # Fetch attendance records for this user in the current quarter
        attendance_records = AttendanceRegister.objects.filter(
            attendant_id=user_id,
            attendance_date__date__range=[quarter_start, quarter_end]
        ).order_by('-attendance_date__date')

        # Calculate average attendance score
        if attendance_records.exists():
            total_score = sum([record.percentage_mark for record in attendance_records])
            average_score = round(total_score / attendance_records.count(), 2)
        else:
            average_score = 0.0

        # Get last 10 attendance records
        last_10 = attendance_records[:10]
        attendance_history = [
            {'date': record.attendance_date.date, 'score': record.percentage_mark}
            for record in last_10
        ]

        return Response({
            'qtr_score': average_score,
            'score_history': attendance_history
        }, status=status.HTTP_200_OK)


class FuelSalesSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        print(user)
        site = user.employee_profile.site if hasattr(user, 'employee_profile') else None

        if not site:
            return Response({'detail': 'User site not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the year from query params, default to current year
        year = int(request.query_params.get('year', now().year))
        today = now().date()
        month = today.month

        # 1. Get all fuel sales for the user's site in the current month
        fuel_sales = FuelSales.objects.filter(date__year=year, date__month=month, user__employee_profile__site=site)

        # Sum of total sales for the current month
        raw_score = sum(sale.pms_sales + sale.dx_sales + sale.vp_sales for sale in fuel_sales)

        # Get monthly target for the user's site: sum of all pump targets * number of days in the month
        pump_daily_target = PumpTarget.objects.filter(site=site).aggregate(total_target=Sum('target'))['total_target'] or 0
        days_in_month = monthrange(year, month)[1]
        monthly_target = pump_daily_target * days_in_month

        current_performance = (raw_score / int(monthly_target)) * 100 if monthly_target > 0 else 0

        # 2. Performance per captain (only customer_champion at user's site)
        captain_data = []
        
        captains = Captain.objects.filter(
            site=site,
            user__employee_profile__job_description__iexact='customer_champion'
        )
        print(captains)
        
        for captain in captains:
            captain_sales = fuel_sales.filter(captain=captain)
            captain_raw_score = sum(sale.pms_sales + sale.dx_sales + sale.vp_sales for sale in captain_sales)
            captain_performance = (captain_raw_score / Decimal(monthly_target / 2)) * 100 if monthly_target > 0 else 0

            captain_data.append({
                'captain': captain.user.employee_profile.name,
                'raw_score': captain_raw_score,
                'target': monthly_target,
                'performance': round(captain_performance, 2)
            })

        # 3. Monthly summary for the selected year
        monthly_summary = []
        for m in range(1, 13):
            month_sales = FuelSales.objects.filter(date__year=year, date__month=m,  user__employee_profile__site=site)
            month_raw_score = sum(sale.pms_sales + sale.dx_sales + sale.vp_sales for sale in month_sales)

            pump_target = PumpTarget.objects.filter(site=site).aggregate(total_target=Sum('target'))['total_target'] or 0
            days_in_month = monthrange(year, m)[1]
            month_target = pump_target * days_in_month

            month_performance = (month_raw_score / Decimal(monthly_target)) * 100 if month_target > 0 else 0

            monthly_summary.append({
                'month': date(1900, m, 1).strftime('%b'),  # Jan, Feb, etc.
                'sales': month_raw_score,
                'target': month_target,
                'percentage': round(month_performance, 2),
                'growth': 0  # We will calculate growth next
            })

        # Calculate growth per month
        for i in range(1, len(monthly_summary)):
            prev_sales = monthly_summary[i - 1]['sales']
            curr_sales = monthly_summary[i]['sales']

            if prev_sales > 0:
                growth = (curr_sales - prev_sales) / prev_sales
            else:
                growth = 0

            monthly_summary[i]['growth'] = round(growth, 2)

        return Response({
            'current_performance': {
                'raw_score': raw_score,
                'target': monthly_target,
                'performance': round(current_performance, 2)
            },
            'captain_performance': captain_data,
            'monthly_summary': monthly_summary
        })





class ShopSalesSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        site = user.employee_profile.site if hasattr(user, 'employee_profile') else None

        if not site:
            return Response({'detail': 'User site not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get the year from query params, default to current year
        year = int(request.query_params.get('year', now().year))
        today = now().date()
        month = today.month

        # 1. Get all shop sales for the user's site in the current month
        shop_sales = ShopSales.objects.filter(date__year=year, date__month=month, user__employee_profile__site=site)

        # Sum of total sales for the current month
        raw_score = sum(sale.sales for sale in shop_sales)

        # Get monthly target for the user's site
        try:
            shop_target = ShopTarget.objects.get(site=site)
            monthly_target = shop_target.target * 30
        except ShopTarget.DoesNotExist:
            monthly_target = 13500 * 30

        current_performance = (raw_score / Decimal(monthly_target)) * 100 if monthly_target > 0 else 0

        # 2. Performance per captain (only customer_champion at user's site)
        captain_data = []
        
        captains = Captain.objects.filter(
            site=site,
            user__employee_profile__job_description__iexact='service_champion'
        )
        
        captain_target = monthly_target / len(captains)
        for captain in captains:
            captain_sales = shop_sales.filter(captain=captain)
            captain_raw_score = sum(sale.sales for sale in captain_sales)
            captain_performance = (captain_raw_score / Decimal(monthly_target/2)) * 100 if monthly_target > 0 else 0

            captain_data.append({
                'captain': captain.user.employee_profile.name,
                'raw_score': captain_raw_score,
                'target': monthly_target/2,
                'performance': round(captain_performance, 2)
            })

        # 3. Monthly summary for the selected year
        monthly_summary = []
        for m in range(1, 13):
            month_sales = ShopSales.objects.filter(date__year=year, date__month=m, user__employee_profile__site=site)
            month_raw_score = sum(sale.sales for sale in month_sales)

            try:
                shop_target = ShopTarget.objects.get(site=site)
                days_in_month = monthrange(year, m)[1]
                month_target = shop_target.target * 30
              
            except ShopTarget.DoesNotExist:
                month_target = 0

            month_performance = (month_raw_score / Decimal(month_target)) * 100 if month_target > 0 else 0

            monthly_summary.append({
                'month': date(1900, m, 1).strftime('%b'),  # Jan, Feb, etc.
                'sales': month_raw_score,
                'target': month_target,
                'percentage': round(month_performance, 2),
                'growth': 0  # We will calculate growth next
            })

        # Calculate growth per month
        for i in range(1, len(monthly_summary)):
            prev_sales = monthly_summary[i - 1]['sales']
            curr_sales = monthly_summary[i]['sales']

            if prev_sales > 0:
                growth = (curr_sales - prev_sales) / prev_sales
            else:
                growth = 0

            monthly_summary[i]['growth'] = round(growth, 2)

        return Response({
            'current_performance': {
                'raw_score': raw_score,
                'target': monthly_target,
                'performance': round(current_performance, 2)
            },
            'captain_performance': captain_data,
            'monthly_summary': monthly_summary
        })