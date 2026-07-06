"""
Auto-Fix API URLs - One-command code fixing
"""

from django.urls import path
from . import auto_fix_views

app_name = 'auto_fix'

urlpatterns = [
    # One-command fixes
    path('now/', auto_fix_views.AutoFixNowView.as_view(), name='fix-now'),
    path('smart/', auto_fix_views.SmartFixView.as_view(), name='smart-fix'),
    path('quick/', auto_fix_views.QuickFixView.as_view(), name='quick-fix'),
    
    # Background continuous fixing
    path('continuous/', auto_fix_views.ContinuousFixView.as_view(), name='continuous-fix'),
]
