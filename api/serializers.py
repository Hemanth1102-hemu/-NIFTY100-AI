from rest_framework import serializers
from core.models import (
    Sector, Company, FinancialFact, BalanceSheet,
    CashFlow, AnalysisFact, ProsCons, MLFact,
)


class SectorSerializer(serializers.ModelSerializer):
    company_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Sector
        fields = '__all__'


class CompanySerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source='sector.name', read_only=True)

    class Meta:
        model = Company
        fields = [
            'id', 'symbol', 'name', 'sector', 'sector_name',
            'industry', 'series', 'isin_code',
            'company_logo', 'website', 'nse_url', 'bse_url',
            'chart_link', 'about_company',
            'face_value', 'book_value', 'roce', 'roe',
        ]


class CompanyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views with computed financials."""
    sector_name = serializers.CharField(source='sector.name', read_only=True)

    class Meta:
        model = Company
        fields = [
            'id', 'symbol', 'name', 'sector', 'sector_name',
            'roe', 'roce', 'face_value', 'book_value',
        ]


class FinancialFactSerializer(serializers.ModelSerializer):
    company_symbol = serializers.CharField(source='company.symbol', read_only=True)

    class Meta:
        model = FinancialFact
        fields = '__all__'


class BalanceSheetSerializer(serializers.ModelSerializer):
    company_symbol = serializers.CharField(source='company.symbol', read_only=True)

    class Meta:
        model = BalanceSheet
        fields = '__all__'


class CashFlowSerializer(serializers.ModelSerializer):
    company_symbol = serializers.CharField(source='company.symbol', read_only=True)

    class Meta:
        model = CashFlow
        fields = '__all__'


class AnalysisFactSerializer(serializers.ModelSerializer):
    company_symbol = serializers.CharField(source='company.symbol', read_only=True)

    class Meta:
        model = AnalysisFact
        fields = '__all__'


class ProsConsSerializer(serializers.ModelSerializer):
    company_symbol = serializers.CharField(source='company.symbol', read_only=True)

    class Meta:
        model = ProsCons
        fields = '__all__'


class MLFactSerializer(serializers.ModelSerializer):
    company_symbol = serializers.CharField(source='company.symbol', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    sector_name = serializers.CharField(source='company.sector.name', read_only=True)

    class Meta:
        model = MLFact
        fields = '__all__'
