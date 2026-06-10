"""
ETL Management Command: load_real_data
Reads all 7 Excel files from data/raw/ and populates every model.
Idempotent – safe to run multiple times via update_or_create.
"""
import os
import re
import math
import pandas as pd
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import (
    Sector, Company, FinancialFact, BalanceSheet,
    CashFlow, AnalysisFact, ProsCons, MLFact,
)

DATA_DIR = os.path.join(settings.BASE_DIR, 'data', 'raw')

# ── Sector classification ────────────────────────────────────
SECTOR_MAP = {
    'IT Services': ['TCS', 'INFY', 'HCLTECH', 'TECHM', 'LTIM', 'WIPRO'],
    'Banking': ['HDFCBANK', 'ICICIBANK', 'AXISBANK', 'KOTAKBANK', 'SBIN',
                'BANKBARODA', 'PNB', 'CANBK', 'INDUSINDBK'],
    'NBFC/Finance': ['BAJFINANCE', 'BAJAJFINSV', 'CHOLAFIN', 'SHRIRAMFIN',
                     'JIOFIN', 'PFC', 'RECLTD', 'IRFC'],
    'Insurance': ['SBILIFE', 'HDFCLIFE', 'ICICIGI', 'ICICIPRULI', 'LICI'],
    'Oil & Gas / Energy': ['RELIANCE', 'ONGC', 'IOC', 'BPCL', 'GAIL',
                           'ADANIENT', 'ADANIPORTS', 'ADANIGREEN',
                           'ADANIENSOL', 'ADANIPOWER', 'ATGL', 'TATAPOWER',
                           'JSWENERGY', 'NTPC', 'NHPC', 'POWERGRID', 'COALINDIA'],
    'Automobile': ['MARUTI', 'BAJAJ-AUTO', 'TATAMOTORS', 'HEROMOTOCO',
                   'EICHERMOT', 'TVSMOTOR', 'M&M', 'MOTHERSON', 'BOSCHLTD'],
    'Consumer Goods/FMCG': ['HINDUNILVR', 'ITC', 'NESTLEIND', 'BRITANNIA',
                            'DABUR', 'GODREJCP', 'TATACONSUM', 'DMART', 'TRENT'],
    'Pharma/Healthcare': ['SUNPHARMA', 'CIPLA', 'DRREDDY', 'DIVISLAB',
                          'TORNTPHARM', 'APOLLOHOSP'],
    'Metals & Mining': ['TATASTEEL', 'JSWSTEEL', 'JINDALSTEL', 'HINDALCO'],
    'Cement & Construction': ['AMBUJACEM', 'SHREECEM', 'GRASIM', 'DLF', 'LODHA', 'LT'],
    'Industrial/Manufacturing': ['ABB', 'BEL', 'BHEL', 'HAL', 'SIEMENS',
                                  'HAVELLS', 'PIDILITIND'],
    'Paint': ['ASIANPAINT'],
    'Telecom': ['BHARTIARTL'],
    'Travel/Transport': ['INDIGO', 'IRCTC'],
    'Holding': ['BAJAJHLDNG'],
    'Internet/Tech': ['NAUKRI'],
    'Jewellery/Retail': ['TITAN'],
}

# Reverse lookup: symbol -> sector name
SYMBOL_TO_SECTOR = {}
for sector_name, symbols in SECTOR_MAP.items():
    for sym in symbols:
        SYMBOL_TO_SECTOR[sym] = sector_name


# ── Helpers ───────────────────────────────────────────────────
def safe_float(val, default=0.0):
    """Convert any value to float; return *default* on failure."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    try:
        # strip common non-numeric chars like % or commas
        cleaned = str(val).replace(',', '').replace('%', '').strip()
        if cleaned == '' or cleaned == '-':
            return default
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def safe_decimal(val, default=0):
    return Decimal(str(safe_float(val, float(default))))


def read_excel_real(filename):
    """Read Excel with row 1=banner, row 2=headers, row 3+=data."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    df = pd.read_excel(path, header=1)  # row index 1 = second row = headers
    return df


def parse_year(year_str):
    """
    Parse year strings from Excel columns.
    Returns (fiscal_year: int, month: str, is_ttm: bool)
    Examples:
      'Mar 2024'      -> (2024, 'Mar', False)
      'Mar-24'        -> (2024, 'Mar', False)
      'Dec 2023'      -> (2023, 'Dec', False)
      'TTM'           -> (9999, 'TTM', True)
      'Mar 2016 9m'   -> (2016, 'Mar', False)
      'Mar 2023 15'   -> (2023, 'Mar', False)
    """
    if year_str is None:
        return (0, '', False)
    s = str(year_str).strip()
    if s.upper() == 'TTM':
        return (9999, 'TTM', True)

    # Pattern: 'Mar 2024', 'Mar 2016 9m', 'Dec 2023', 'Jun 2015'
    m = re.match(r'^([A-Za-z]+)\s+(\d{4})', s)
    if m:
        month = m.group(1).capitalize()
        fy = int(m.group(2))
        return (fy, month, False)

    # Pattern: 'Mar-24', 'Mar-13'
    m = re.match(r'^([A-Za-z]+)-(\d{2})$', s)
    if m:
        month = m.group(1).capitalize()
        yr2 = int(m.group(2))
        fy = 2000 + yr2 if yr2 < 50 else 1900 + yr2
        return (fy, month, False)

    # Just a number like '2024'
    m = re.match(r'^(\d{4})$', s)
    if m:
        return (int(m.group(1)), '', False)

    return (0, '', False)


def parse_analysis_string(raw):
    """
    Parse strings like '10 Years: 21%\n5 Years: 24%\nTTM: 43%'
    Returns list of (period, value) tuples.
    """
    results = []
    if not raw or (isinstance(raw, float) and math.isnan(raw)):
        return results
    for line in str(raw).split('\n'):
        line = line.strip()
        if not line:
            continue
        # Handle both "10 Years: 21%" and "TTM: 43%"
        m = re.match(r'^(.+?):\s*([\-\d.]+)%?$', line)
        if m:
            period = m.group(1).strip()
            try:
                value = float(m.group(2))
            except ValueError:
                value = 0.0
            results.append((period, value))
    return results


class Command(BaseCommand):
    help = 'Load real Nifty 100 data from Excel files into all models'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== Starting Real Data ETL ==='))

        self._load_sectors()
        company_map = self._load_companies()
        self._load_profit_loss(company_map)
        self._load_balance_sheets(company_map)
        self._load_cash_flows(company_map)
        self._load_analysis(company_map)
        self._load_pros_cons(company_map)
        self._compute_ml_scores(company_map)

        self.stdout.write(self.style.SUCCESS('=== ETL Complete! ==='))

    # ── 1. Sectors ────────────────────────────────────────────
    def _load_sectors(self):
        self.stdout.write('Loading sectors...')
        for name in SECTOR_MAP.keys():
            code = name.lower().replace(' ', '_').replace('/', '_').replace('&', 'and')
            Sector.objects.update_or_create(
                name=name,
                defaults={'sector_code': code, 'description': f'{name} sector companies in Nifty 100'},
            )
        self.stdout.write(self.style.SUCCESS(f'  -> {Sector.objects.count()} sectors loaded'))

    # ── 2. Companies ──────────────────────────────────────────
    def _load_companies(self):
        self.stdout.write('Loading companies from companies.xlsx...')
        df = read_excel_real('companies.xlsx')
        self.stdout.write(f'  -> Read {len(df)} rows, columns: {list(df.columns)}')

        # Build a map of sector name -> Sector object
        sector_objs = {s.name: s for s in Sector.objects.all()}
        # Fallback sector
        other_sector, _ = Sector.objects.get_or_create(
            name='Other', defaults={'sector_code': 'other', 'description': 'Unclassified'}
        )

        company_map = {}  # symbol -> Company object
        for _, row in df.iterrows():
            symbol = str(row.get('id', '')).strip()
            if not symbol:
                continue
            company_name = str(row.get('company_name', symbol)).strip()
            sector_name = SYMBOL_TO_SECTOR.get(symbol, 'Other')
            sector_obj = sector_objs.get(sector_name, other_sector)

            comp, created = Company.objects.update_or_create(
                symbol=symbol,
                defaults={
                    'name': company_name,
                    'sector': sector_obj,
                    'company_logo': str(row.get('company_logo', '') or '').strip() or None,
                    'website': str(row.get('website', '') or '').strip() or None,
                    'nse_url': str(row.get('nse_profile', '') or '').strip() or None,
                    'bse_url': str(row.get('bse_profile', '') or '').strip() or None,
                    'chart_link': str(row.get('chart_link', '') or '').strip() or None,
                    'about_company': str(row.get('about_company', '') or '').strip() or None,
                    'face_value': safe_decimal(row.get('face_value'), 0),
                    'book_value': safe_decimal(row.get('book_value'), 0),
                    'roce': safe_decimal(row.get('roce_percentage'), 0),
                    'roe': safe_decimal(row.get('roe_percentage'), 0),
                },
            )
            company_map[symbol] = comp

        self.stdout.write(self.style.SUCCESS(f'  -> {len(company_map)} companies loaded'))
        return company_map

    # ── 3. Profit & Loss ──────────────────────────────────────
    def _load_profit_loss(self, company_map):
        self.stdout.write('Loading P&L from profitandloss.xlsx...')
        df = read_excel_real('profitandloss.xlsx')
        self.stdout.write(f'  -> Read {len(df)} rows, columns: {list(df.columns)}')
        count = 0
        for _, row in df.iterrows():
            cid = str(row.get('company_id', '')).strip()
            comp = company_map.get(cid)
            if not comp:
                continue

            fy, month, is_ttm = parse_year(row.get('year'))
            if fy == 0:
                continue

            quarter = month or ('TTM' if is_ttm else 'AN')
            sales_val = safe_float(row.get('sales'))
            np_val = safe_float(row.get('net_profit'))
            opm_val = safe_float(row.get('opm_percentage'))
            op_val = safe_float(row.get('operating_profit'))

            FinancialFact.objects.update_or_create(
                company=comp, year=fy, quarter=quarter,
                defaults={
                    'month': month,
                    'is_ttm': is_ttm,
                    'revenue': safe_decimal(sales_val),
                    'sales': safe_decimal(sales_val),
                    'expenses': safe_decimal(row.get('expenses')),
                    'operating_profit': safe_decimal(op_val),
                    'opm_percentage': safe_decimal(opm_val),
                    'opm': safe_decimal(opm_val),
                    'other_income': safe_decimal(row.get('other_income')),
                    'interest': safe_decimal(row.get('interest')),
                    'depreciation': safe_decimal(row.get('depreciation')),
                    'profit_before_tax': safe_decimal(row.get('profit_before_tax')),
                    'tax_percentage': safe_decimal(row.get('tax_percentage')),
                    'net_profit': safe_decimal(np_val),
                    'eps': safe_decimal(row.get('eps')),
                    'dividend_payout': safe_decimal(row.get('dividend_payout')),
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f'  -> {count} P&L rows loaded'))

    # ── 4. Balance Sheet ──────────────────────────────────────
    def _load_balance_sheets(self, company_map):
        self.stdout.write('Loading Balance Sheets from balancesheet.xlsx...')
        df = read_excel_real('balancesheet.xlsx')
        self.stdout.write(f'  -> Read {len(df)} rows, columns: {list(df.columns)}')
        count = 0
        for _, row in df.iterrows():
            cid = str(row.get('company_id', '')).strip()
            comp = company_map.get(cid)
            if not comp:
                continue

            fy, month, is_ttm = parse_year(row.get('year'))
            if fy == 0:
                continue
            month_key = month or ('TTM' if is_ttm else 'AN')

            borrowings_val = safe_float(row.get('borrowings'))
            equity_val = safe_float(row.get('equity_capital'))
            reserves_val = safe_float(row.get('reserves'))
            shareholder_equity = equity_val + reserves_val

            BalanceSheet.objects.update_or_create(
                company=comp, year=fy, month=month_key,
                defaults={
                    'is_ttm': is_ttm,
                    'equity_capital': safe_decimal(equity_val),
                    'reserves': safe_decimal(reserves_val),
                    'borrowings': safe_decimal(borrowings_val),
                    'other_liabilities': safe_decimal(row.get('other_liabilities')),
                    'total_liabilities': safe_decimal(row.get('total_liabilities')),
                    'fixed_assets': safe_decimal(row.get('fixed_assets')),
                    'cwip': safe_decimal(row.get('cwip')),
                    'investments': safe_decimal(row.get('investments')),
                    'other_assets': safe_decimal(row.get('other_asset')),
                    'total_assets': safe_decimal(row.get('total_assets')),
                },
            )
            count += 1

            # Also update the FinancialFact with D/E and total_assets if exists
            de_ratio = 0
            if shareholder_equity > 0:
                de_ratio = round(borrowings_val / shareholder_equity, 2)
            FinancialFact.objects.filter(
                company=comp, year=fy
            ).update(
                debt_to_equity=safe_decimal(de_ratio),
                total_assets=safe_decimal(row.get('total_assets')),
                total_liabilities=safe_decimal(row.get('total_liabilities')),
            )

        self.stdout.write(self.style.SUCCESS(f'  -> {count} balance sheet rows loaded'))

    # ── 5. Cash Flow ──────────────────────────────────────────
    def _load_cash_flows(self, company_map):
        self.stdout.write('Loading Cash Flows from cashflow.xlsx...')
        df = read_excel_real('cashflow.xlsx')
        self.stdout.write(f'  -> Read {len(df)} rows, columns: {list(df.columns)}')
        count = 0
        for _, row in df.iterrows():
            cid = str(row.get('company_id', '')).strip()
            comp = company_map.get(cid)
            if not comp:
                continue

            fy, month, is_ttm = parse_year(row.get('year'))
            if fy == 0:
                continue
            month_key = month or ('TTM' if is_ttm else 'AN')

            ocf = safe_float(row.get('operating_activity'))

            CashFlow.objects.update_or_create(
                company=comp, year=fy, month=month_key,
                defaults={
                    'is_ttm': is_ttm,
                    'operating_activity': safe_decimal(ocf),
                    'investing_activity': safe_decimal(row.get('investing_activity')),
                    'financing_activity': safe_decimal(row.get('financing_activity')),
                    'net_cash_flow': safe_decimal(row.get('net_cash_flow')),
                },
            )
            count += 1

            # Backfill operating_cash_flow into FinancialFact
            FinancialFact.objects.filter(company=comp, year=fy).update(
                operating_cash_flow=safe_decimal(ocf),
            )

        self.stdout.write(self.style.SUCCESS(f'  -> {count} cash flow rows loaded'))

    # ── 6. Analysis ───────────────────────────────────────────
    def _load_analysis(self, company_map):
        self.stdout.write('Loading Analysis from analysis.xlsx...')
        df = read_excel_real('analysis.xlsx')
        self.stdout.write(f'  -> Read {len(df)} rows, columns: {list(df.columns)}')
        count = 0
        metric_cols = ['compounded_sales_growth', 'compounded_profit_growth',
                       'stock_price_cagr', 'roe']
        for _, row in df.iterrows():
            cid = str(row.get('company_id', '')).strip()
            comp = company_map.get(cid)
            if not comp:
                continue

            for col in metric_cols:
                raw = row.get(col)
                pairs = parse_analysis_string(raw)
                for period, value in pairs:
                    AnalysisFact.objects.update_or_create(
                        company=comp, metric=col, period=period,
                        defaults={'value': safe_decimal(value)},
                    )
                    count += 1

        self.stdout.write(self.style.SUCCESS(f'  -> {count} analysis facts loaded'))

    # ── 7. Pros & Cons ────────────────────────────────────────
    def _load_pros_cons(self, company_map):
        self.stdout.write('Loading Pros & Cons from prosandcons.xlsx...')
        df = read_excel_real('prosandcons.xlsx')
        self.stdout.write(f'  -> Read {len(df)} rows, columns: {list(df.columns)}')
        count = 0
        for _, row in df.iterrows():
            cid = str(row.get('company_id', '')).strip()
            comp = company_map.get(cid)
            if not comp:
                continue

            pros_text = str(row.get('pros', '') or '').strip()
            cons_text = str(row.get('cons', '') or '').strip()

            ProsCons.objects.update_or_create(
                company=comp,
                defaults={'pros': pros_text, 'cons': cons_text},
            )
            count += 1

        self.stdout.write(self.style.SUCCESS(f'  -> {count} pros/cons loaded'))

    # ── 8. ML Health Scores ───────────────────────────────────
    def _compute_ml_scores(self, company_map):
        self.stdout.write('Computing ML health scores...')
        count = 0

        for symbol, comp in company_map.items():
            # Get all P&L records sorted by year
            pnl_qs = comp.financials.filter(is_ttm=False).order_by('year')
            pnl_list = list(pnl_qs)
            if not pnl_list:
                continue

            latest = pnl_list[-1]
            latest_year = latest.year

            # ─ Profitability (25%) ─
            opm_pct = float(latest.opm_percentage or 0)
            sales_v = float(latest.sales or 0)
            np_v = float(latest.net_profit or 0)
            npm = (np_v / sales_v * 100) if sales_v > 0 else 0
            prof_raw = min(opm_pct * 1.5 + npm * 1.0, 100)
            profitability = max(0, min(100, prof_raw))

            # ─ Growth (20%) ─
            growth = 50  # default neutral
            if len(pnl_list) >= 4:
                old_sales = float(pnl_list[-4].sales or 0)
                new_sales = float(latest.sales or 0)
                if old_sales > 0:
                    cagr = ((new_sales / old_sales) ** (1 / 3) - 1) * 100
                    growth = max(0, min(100, 50 + cagr * 2))

            # ─ Leverage (20%) ─
            de = float(latest.debt_to_equity or 0)
            if de <= 0.1:
                leverage = 100
            elif de <= 0.5:
                leverage = 80
            elif de <= 1.0:
                leverage = 60
            elif de <= 1.5:
                leverage = 40
            elif de <= 2.0:
                leverage = 20
            else:
                leverage = 5

            # ─ Cash Flow (15%) ─
            cashflow_score = 50
            cf_qs = comp.cash_flows.filter(year=latest_year).first()
            if cf_qs:
                ocf = float(cf_qs.operating_activity or 0)
                if np_v > 0:
                    ratio = ocf / np_v
                    if ratio > 1.5:
                        cashflow_score = 100
                    elif ratio > 1.0:
                        cashflow_score = 85
                    elif ratio > 0.5:
                        cashflow_score = 60
                    else:
                        cashflow_score = 30
                elif ocf > 0:
                    cashflow_score = 40
                else:
                    cashflow_score = 10

            # ─ Dividend (10%) ─
            div_payouts = [float(p.dividend_payout or 0) for p in pnl_list[-5:]]
            avg_div = sum(div_payouts) / len(div_payouts) if div_payouts else 0
            if avg_div >= 30:
                dividend = 100
            elif avg_div >= 20:
                dividend = 80
            elif avg_div >= 10:
                dividend = 60
            elif avg_div > 0:
                dividend = 40
            else:
                dividend = 10

            # ─ Trend (10%) ─
            trend = 50
            if len(pnl_list) >= 3:
                opms_recent = [float(p.opm_percentage or 0) for p in pnl_list[-3:]]
                if opms_recent[-1] > opms_recent[0]:
                    trend = 80
                elif opms_recent[-1] < opms_recent[0]:
                    trend = 30
                profits_recent = [float(p.net_profit or 0) for p in pnl_list[-3:]]
                if profits_recent[-1] > profits_recent[0] and profits_recent[-1] > 0:
                    trend = min(trend + 20, 100)

            # ─ Weighted final score ─
            health_score = int(round(
                profitability * 0.25 +
                growth * 0.20 +
                leverage * 0.20 +
                cashflow_score * 0.15 +
                dividend * 0.10 +
                trend * 0.10
            ))
            health_score = max(0, min(100, health_score))

            # Label
            if health_score >= 85:
                label = 'EXCELLENT'
            elif health_score >= 70:
                label = 'GOOD'
            elif health_score >= 50:
                label = 'AVERAGE'
            elif health_score >= 35:
                label = 'WEAK'
            else:
                label = 'POOR'

            # Anomaly detection (simple heuristic)
            anomaly = False
            anomaly_desc = ''
            if de > 2.0:
                anomaly = True
                anomaly_desc = 'Very high debt-to-equity ratio'
            elif np_v < 0:
                anomaly = True
                anomaly_desc = 'Negative net profit in latest year'
            elif opm_pct < 0:
                anomaly = True
                anomaly_desc = 'Negative operating margin'

            # Cluster (simple grouping by health score range)
            if health_score >= 75:
                cluster = 1
            elif health_score >= 55:
                cluster = 2
            elif health_score >= 35:
                cluster = 3
            else:
                cluster = 4

            # Auto Pros/Cons
            auto_pros_list = []
            auto_cons_list = []
            if de < 0.1:
                auto_pros_list.append('Company is almost debt free')
            roe_comp = float(comp.roe or 0)
            if roe_comp > 20:
                auto_pros_list.append('Good ROE track record')
            if avg_div >= 30:
                auto_pros_list.append('Healthy dividend payout')
            if len(pnl_list) >= 3:
                opms_3 = [float(p.opm_percentage or 0) for p in pnl_list[-3:]]
                if opms_3[-1] > opms_3[0]:
                    auto_pros_list.append('Improving operating margins')
                if opms_3[-1] < opms_3[0]:
                    auto_cons_list.append('Declining operating margins')
            if de > 1.5:
                auto_cons_list.append('High debt levels')
            if npm < 5 and sales_v > 0:
                auto_cons_list.append('Low net profit margin')

            # Revenue forecast (simple: 10% growth from latest)
            rev_forecast = Decimal(str(round(float(latest.sales or 0) * 1.10, 2)))

            MLFact.objects.update_or_create(
                company=comp, year=latest_year,
                defaults={
                    'health_score': health_score,
                    'health_label': label,
                    'anomaly_status': anomaly,
                    'anomaly_description': anomaly_desc,
                    'cluster_group': cluster,
                    'revenue_forecast': rev_forecast,
                    'profitability_score': safe_decimal(profitability),
                    'growth_score': safe_decimal(growth),
                    'leverage_score': safe_decimal(leverage),
                    'cashflow_score': safe_decimal(cashflow_score),
                    'dividend_score': safe_decimal(dividend),
                    'trend_score': safe_decimal(trend),
                    'auto_pros': '\n'.join(auto_pros_list),
                    'auto_cons': '\n'.join(auto_cons_list),
                },
            )
            count += 1

            # Also update Company ROE from FinancialFact if not already set
            if comp.roe == 0 and npm > 0:
                bs = comp.balance_sheets.filter(year=latest_year).first()
                if bs:
                    eq = float(bs.equity_capital or 0) + float(bs.reserves or 0)
                    if eq > 0:
                        comp.roe = Decimal(str(round(np_v / eq * 100, 2)))
                        comp.save(update_fields=['roe'])

        self.stdout.write(self.style.SUCCESS(f'  -> {count} ML scores computed'))
