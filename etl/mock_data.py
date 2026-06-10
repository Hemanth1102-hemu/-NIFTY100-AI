import os
import sys
import django
import random
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nifty_intel.settings')
django.setup()

from core.models import Sector, Company, FinancialFact, MLFact

def generate_mock_data():
    sectors_data = [
        "IT Services", "Banking", "Automobile", "Consumer Goods", 
        "Oil & Gas", "Pharmaceuticals", "Metals & Mining", "Construction"
    ]
    
    sectors = []
    for s_name in sectors_data:
        sector, _ = Sector.objects.get_or_create(name=s_name)
        sectors.append(sector)
    
    companies_data = [
        {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT Services"},
        {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Oil & Gas"},
        {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking"},
        {"symbol": "INFY", "name": "Infosys", "sector": "IT Services"},
        {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking"},
        {"symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "Consumer Goods"},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel", "sector": "IT Services"},
        {"symbol": "ITC", "name": "ITC Limited", "sector": "Consumer Goods"},
        {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
        {"symbol": "MARUTI", "name": "Maruti Suzuki", "sector": "Automobile"},
    ]
    
    for c_data in companies_data:
        sector = Sector.objects.get(name=c_data['sector'])
        company, _ = Company.objects.get_or_create(
            symbol=c_data['symbol'],
            defaults={'name': c_data['name'], 'sector': sector}
        )
        
        # Generate Financials for last 3 years
        for year in [2022, 2023, 2024]:
            rev = Decimal(random.uniform(50000, 500000))
            profit = rev * Decimal(random.uniform(0.1, 0.25))
            assets = rev * Decimal(random.uniform(1.5, 3.0))
            liabilities = assets * Decimal(random.uniform(0.3, 0.7))
            
            # Ratios
            roe = (profit / (assets - liabilities)) * 100
            debt_to_equity = liabilities / (assets - liabilities)
            opm = (profit / rev) * 100
            
            FinancialFact.objects.get_or_create(
                company=company,
                year=year,
                quarter='AN',
                defaults={
                    'revenue': rev,
                    'net_profit': profit,
                    'total_assets': assets,
                    'total_liabilities': liabilities,
                    'operating_cash_flow': profit * Decimal(0.8),
                    'roe': roe,
                    'debt_to_equity': debt_to_equity,
                    'opm': opm,
                    'pe_ratio': Decimal(random.uniform(15, 40))
                }
            )
            
            # Generate ML Insights
            MLFact.objects.get_or_create(
                company=company,
                year=year,
                defaults={
                    'health_score': random.randint(60, 95),
                    'anomaly_status': random.random() < 0.1,
                    'anomaly_description': "Suspicious growth in other income" if random.random() < 0.1 else "",
                    'cluster_group': random.randint(1, 4),
                    'revenue_forecast': rev * Decimal(1.1)
                }
            )

    print("Mock data generated successfully!")

if __name__ == "__main__":
    generate_mock_data()
