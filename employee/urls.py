from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .auth_token import CustomAuthToken

from .viewset import (EmployeeViewSet, FuelSalesViewSet, ShopSalesViewSet, BulkAttendanceViewSet,
                      CreditSalesViewSet, CreditCollectionViewSet, CaptainViewSet, CaptainViewSetShop,
                      ActiveAttendantViewSet, WeeklyEvaluationViewSet, WeeklyEvaluationViewSetPost)


from .viewsummary import (UserPerformanceSummaryFuel, EvaluationSummaryView, CombinedPerformanceView,
                          AttendanceSummaryView, FuelSalesSummaryView, ShopSalesSummaryView)


router = DefaultRouter()
router.register(r'employees', EmployeeViewSet)
router.register(r'fuel-sales', FuelSalesViewSet)
router.register(r'shop-sales', ShopSalesViewSet)
router.register(r'weekly-evaluations', WeeklyEvaluationViewSet, basename='weekly-evaluations')
router.register(r'weekly-evaluations-post', WeeklyEvaluationViewSetPost, basename='weekly-evaluations-post')
router.register(r'credit-sales', CreditSalesViewSet)
router.register(r'credit-collections', CreditCollectionViewSet)
router.register(r'captains-pump', CaptainViewSet, basename='pump-captain')
router.register(r'captains-shop', CaptainViewSetShop, basename='shop-captain')
router.register(r'active-attendants', ActiveAttendantViewSet, basename='active-attendant')
router.register(r'daily-attendance-post', BulkAttendanceViewSet, basename='daily-attendance-post')




urlpatterns = [
    path('api/', include(router.urls)),
    path('api/token-auth/', CustomAuthToken.as_view(), name='api_token_auth'),
    path('api/fuel-performance-summary/', UserPerformanceSummaryFuel.as_view(), name='performance-summary'),
    path('api/fuel-performance-summary/<int:user_id>/', UserPerformanceSummaryFuel.as_view(), name='performance-summary-user'),
    path('api/evaluation-summary/', EvaluationSummaryView.as_view(), name='evaluation-summary'),
    path('api/evaluation-summary/<int:user_id>/', EvaluationSummaryView.as_view(), name='evaluation-summary-user'),
    path('api/attendance-summary/', AttendanceSummaryView.as_view(), name='attendance-summary'),
    path('api/attendance-summary/<int:user_id>/', AttendanceSummaryView.as_view(), name='attendance-summary-user'),
    path('api/fuel-sales-summary/', FuelSalesSummaryView.as_view(), name='fuel-sales-summary'),
     path('api/shop-sales-summary/', ShopSalesSummaryView.as_view(), name='shop-sales-summary'),
    
    
    
    
    
    
    path('api/evaluation-summary-all/', CombinedPerformanceView.as_view(), name='evaluation-summary-all'),
   
    

    
]