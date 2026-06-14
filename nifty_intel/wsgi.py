"""
WSGI config for nifty_intel project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nifty_intel.settings')

application = get_wsgi_application()

try:
    from django.core.management import call_command
    call_command('migrate', interactive=False)
    
    # Auto-load real data if not present
    from core.models import Company
    if Company.objects.filter(financials__sales__gt=0).count() == 0:
        print("Real data not loaded. Running load_real_data...")
        call_command('load_real_data', interactive=False)
except Exception as e:
    print(f"Error running auto-migrations/ETL: {e}")
