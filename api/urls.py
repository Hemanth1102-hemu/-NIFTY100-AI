from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SectorViewSet, CompanyViewSet, FinancialFactViewSet,
    BalanceSheetViewSet, CashFlowViewSet, AnalysisFactViewSet,
    MLFactViewSet, DashboardSummaryView,
)

router = DefaultRouter()
router.register(r'sectors', SectorViewSet)
router.register(r'companies', CompanyViewSet)
router.register(r'financials', FinancialFactViewSet)
router.register(r'balance-sheets', BalanceSheetViewSet)
router.register(r'cash-flows', CashFlowViewSet)
router.register(r'analysis', AnalysisFactViewSet)
router.register(r'ml-scores', MLFactViewSet, basename='ml-scores')

urlpatterns = [
    path('dashboard-summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('', include(router.urls)),
]
