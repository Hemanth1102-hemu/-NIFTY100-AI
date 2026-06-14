"""
URL configuration for nifty_intel project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.http import JsonResponse
import traceback
import sys
from io import StringIO

def debug_etl_view(request):
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = mystdout = StringIO()
    sys.stderr = mystderr = StringIO()
    try:
        from django.core.management import call_command
        call_command('load_real_data', interactive=False)
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        return JsonResponse({"status": "success", "stdout": mystdout.getvalue(), "stderr": mystderr.getvalue()})
    except Exception as e:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        return JsonResponse({
            "status": "error",
            "error": str(e),
            "stdout": mystdout.getvalue(),
            "stderr": mystderr.getvalue(),
            "traceback": traceback.format_exc()
        })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('debug-etl/', debug_etl_view),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
]
