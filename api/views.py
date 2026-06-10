from rest_framework import viewsets, filters
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.views import APIView
from django.db.models import Avg, Sum, Count, Max, Q
from core.models import (
    Sector, Company, FinancialFact, BalanceSheet,
    CashFlow, AnalysisFact, ProsCons, MLFact,
)
from .serializers import (
    SectorSerializer, CompanySerializer, CompanyListSerializer,
    FinancialFactSerializer, BalanceSheetSerializer, CashFlowSerializer,
    AnalysisFactSerializer, ProsConsSerializer, MLFactSerializer,
)


class SectorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer


class CompanyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Company.objects.select_related('sector').all()
    serializer_class = CompanySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['symbol', 'name', 'sector__name']

    @action(detail=True, methods=['get'])
    def financials(self, request, pk=None):
        company = self.get_object()
        financials = company.financials.all().order_by('year')
        serializer = FinancialFactSerializer(financials, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def balance_sheet(self, request, pk=None):
        company = self.get_object()
        data = company.balance_sheets.all().order_by('year')
        serializer = BalanceSheetSerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def cash_flow(self, request, pk=None):
        company = self.get_object()
        data = company.cash_flows.all().order_by('year')
        serializer = CashFlowSerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def analysis(self, request, pk=None):
        company = self.get_object()
        data = company.analysis_facts.all()
        serializer = AnalysisFactSerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def ml_score(self, request, pk=None):
        company = self.get_object()
        data = company.ml_insights.all().order_by('-year')
        serializer = MLFactSerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def pros_cons(self, request, pk=None):
        company = self.get_object()
        data = company.pros_cons.all()
        serializer = ProsConsSerializer(data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='ml_insights')
    def ml_insights(self, request, pk=None):
        company = self.get_object()
        insights = company.ml_insights.all().order_by('-year')
        serializer = MLFactSerializer(insights, many=True)
        return Response(serializer.data)


class FinancialFactViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinancialFact.objects.select_related('company').all()
    serializer_class = FinancialFactSerializer


class BalanceSheetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BalanceSheet.objects.select_related('company').all()
    serializer_class = BalanceSheetSerializer


class CashFlowViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CashFlow.objects.select_related('company').all()
    serializer_class = CashFlowSerializer


class AnalysisFactViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AnalysisFact.objects.select_related('company').all()
    serializer_class = AnalysisFactSerializer


class MLFactViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MLFact.objects.select_related('company', 'company__sector').all()
    serializer_class = MLFactSerializer


class DashboardSummaryView(APIView):
    """
    Returns pre-computed dashboard KPIs so the frontend doesn't need to
    compute anything from fake data.
    """

    def get(self, request):
        companies = Company.objects.select_related('sector').all()
        total_companies = companies.count()

        # Build companies list with latest financials + ML score
        companies_list = []
        total_revenue = 0
        opm_sum = 0
        opm_count = 0

        for comp in companies:
            # Get the latest non-TTM P&L row
            latest_pnl = comp.financials.filter(is_ttm=False).order_by('-year').first()
            # Get latest ML score
            ml = comp.ml_insights.order_by('-year').first()
            # Get latest balance sheet for D/E
            latest_bs = comp.balance_sheets.filter(is_ttm=False).order_by('-year').first()

            rev = float(latest_pnl.sales or 0) if latest_pnl else 0
            np_val = float(latest_pnl.net_profit or 0) if latest_pnl else 0
            opm_val = float(latest_pnl.opm_percentage or 0) if latest_pnl else 0
            de_val = float(latest_pnl.debt_to_equity or 0) if latest_pnl else 0
            roe_val = float(comp.roe or 0)
            health = ml.health_score if ml else 0
            health_label = ml.health_label if ml else 'N/A'
            anomaly = ml.anomaly_status if ml else False
            cluster = ml.cluster_group if ml else 0

            total_revenue += rev
            if opm_val != 0:
                opm_sum += opm_val
                opm_count += 1

            companies_list.append({
                'id': comp.id,
                'symbol': comp.symbol,
                'name': comp.name,
                'sector': comp.sector_id,
                'sector_name': comp.sector.name,
                'revenue': rev,
                'net_profit': np_val,
                'roe': roe_val,
                'opm': opm_val,
                'debt_to_equity': de_val,
                'health_score': health,
                'health_label': health_label,
                'anomaly': anomaly,
                'cluster': cluster,
                'year': latest_pnl.year if latest_pnl else 0,
            })

        avg_opm = round(opm_sum / opm_count, 2) if opm_count else 0

        # Sector summary
        sector_summary = []
        sectors = Sector.objects.all()
        for sec in sectors:
            sec_companies = [c for c in companies_list if c['sector_name'] == sec.name]
            if not sec_companies:
                continue
            sec_rev = sum(c['revenue'] for c in sec_companies)
            sec_avg_health = round(
                sum(c['health_score'] for c in sec_companies) / len(sec_companies), 1
            ) if sec_companies else 0
            sec_avg_opm = round(
                sum(c['opm'] for c in sec_companies) / len(sec_companies), 1
            ) if sec_companies else 0
            sector_summary.append({
                'name': sec.name,
                'count': len(sec_companies),
                'total_revenue': sec_rev,
                'avg_health': sec_avg_health,
                'avg_opm': sec_avg_opm,
            })

        # Health distribution
        excellent = sum(1 for c in companies_list if c['health_score'] >= 85)
        good = sum(1 for c in companies_list if 70 <= c['health_score'] < 85)
        average = sum(1 for c in companies_list if 50 <= c['health_score'] < 70)
        weak = sum(1 for c in companies_list if 35 <= c['health_score'] < 50)
        poor = sum(1 for c in companies_list if c['health_score'] < 35)

        return Response({
            'total_companies': total_companies,
            'total_revenue': round(total_revenue, 2),
            'avg_opm': avg_opm,
            'companies_list': companies_list,
            'sector_summary': sector_summary,
            'health_distribution': {
                'excellent': excellent,
                'good': good,
                'average': average,
                'weak': weak,
                'poor': poor,
            },
        })
