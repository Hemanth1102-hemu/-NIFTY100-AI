import os
import sys
import django
import pandas as pd

# Setup Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nifty_intel.settings')
django.setup()

from core.models import FinancialFact

def export_to_csv():
    data = FinancialFact.objects.select_related('company', 'company__sector').all()
    rows = []
    for item in data:
        rows.append({
            'Symbol': item.company.symbol,
            'Company_Name': item.company.name,
            'Sector': item.company.sector.name,
            'Year': item.year,
            'Quarter': item.quarter,
            'Revenue': float(item.revenue),
            'Net_Profit': float(item.net_profit),
            'Total_Assets': float(item.total_assets),
            'Total_Liabilities': float(item.total_liabilities),
            'ROE': float(item.roe),
            'D/E_Ratio': float(item.debt_to_equity),
            'OPM': float(item.opm),
            'PE_Ratio': float(item.pe_ratio)
        })
    
    df = pd.DataFrame(rows)
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'nifty_100_financials.csv'))
    df.to_csv(output_path, index=False)
    print(f"Data exported successfully to {output_path}")

if __name__ == "__main__":
    export_to_csv()
