from django.db import models


class Sector(models.Model):
    name = models.CharField(max_length=100, unique=True)
    sector_code = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Company(models.Model):
    symbol = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name='companies')
    industry = models.CharField(max_length=255, blank=True, null=True)
    series = models.CharField(max_length=10, blank=True, null=True)
    isin_code = models.CharField(max_length=20, blank=True, null=True)

    # New fields from companies.xlsx
    company_logo = models.URLField(max_length=500, blank=True, null=True)
    website = models.URLField(max_length=500, blank=True, null=True)
    nse_url = models.URLField(max_length=500, blank=True, null=True)
    bse_url = models.URLField(max_length=500, blank=True, null=True)
    chart_link = models.URLField(max_length=500, blank=True, null=True)
    about_company = models.TextField(blank=True, null=True)
    face_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    book_value = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    roce = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    roe = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.symbol} - {self.name}"


class FinancialFact(models.Model):
    """Profit & Loss data — backward compatible with existing fields."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='financials')
    year = models.IntegerField()
    quarter = models.CharField(max_length=10, blank=True, null=True)
    month = models.CharField(max_length=10, blank=True, null=True)
    is_ttm = models.BooleanField(default=False)

    # Original fields (kept for backward compatibility)
    revenue = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    net_profit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_assets = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_liabilities = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    operating_cash_flow = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    # Original ratio fields (kept)
    roe = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    debt_to_equity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    opm = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pe_ratio = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # New P&L fields from profitandloss.xlsx
    sales = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    expenses = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    operating_profit = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    opm_percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_income = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    interest = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    depreciation = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    profit_before_tax = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    tax_percentage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    eps = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    dividend_payout = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'year', 'quarter')

    def __str__(self):
        return f"{self.company.symbol} - {self.year} {self.quarter or ''}"


class BalanceSheet(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='balance_sheets')
    year = models.IntegerField()
    month = models.CharField(max_length=10, blank=True, null=True)
    is_ttm = models.BooleanField(default=False)

    equity_capital = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    reserves = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    borrowings = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    other_liabilities = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_liabilities = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    fixed_assets = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    cwip = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    investments = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    other_assets = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    total_assets = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'year', 'month')

    def __str__(self):
        return f"BS: {self.company.symbol} - {self.year}"


class CashFlow(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='cash_flows')
    year = models.IntegerField()
    month = models.CharField(max_length=10, blank=True, null=True)
    is_ttm = models.BooleanField(default=False)

    operating_activity = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    investing_activity = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    financing_activity = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    net_cash_flow = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'year', 'month')

    def __str__(self):
        return f"CF: {self.company.symbol} - {self.year}"


class AnalysisFact(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='analysis_facts')
    metric = models.CharField(max_length=100)  # e.g. compounded_sales_growth, stock_price_cagr
    period = models.CharField(max_length=50)   # e.g. '10 Years', '5 Years', 'TTM', '3 Years'
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'metric', 'period')

    def __str__(self):
        return f"Analysis: {self.company.symbol} - {self.metric} ({self.period})"


class ProsCons(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='pros_cons')
    pros = models.TextField(blank=True, null=True)
    cons = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Pros and Cons'

    def __str__(self):
        return f"ProsCons: {self.company.symbol}"


class MLFact(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='ml_insights')
    year = models.IntegerField()

    health_score = models.IntegerField(default=0)
    health_label = models.CharField(max_length=20, blank=True, null=True)  # EXCELLENT, GOOD, AVERAGE, WEAK, POOR
    anomaly_status = models.BooleanField(default=False)
    anomaly_description = models.TextField(blank=True, null=True)
    cluster_group = models.IntegerField(default=0)
    revenue_forecast = models.DecimalField(max_digits=20, decimal_places=2, blank=True, null=True)

    # 6-dimension scoring
    profitability_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    growth_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    leverage_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cashflow_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    dividend_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    trend_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Auto-generated insights
    auto_pros = models.TextField(blank=True, null=True)
    auto_cons = models.TextField(blank=True, null=True)

    last_computed = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('company', 'year')

    def __str__(self):
        return f"ML Insights: {self.company.symbol} - {self.year}"
