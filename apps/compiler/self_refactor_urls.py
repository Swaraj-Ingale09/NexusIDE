"""
Self-Refactoring API URLs
"""

from django.urls import path
from . import self_refactor_views

app_name = 'self_refactor'

urlpatterns = [
    # Analysis
    path('analyze/', self_refactor_views.CodeAnalysisView.as_view(), name='analyze'),
    path('metrics/', self_refactor_views.CodeMetricsView.as_view(), name='metrics'),
    path('statistics/', self_refactor_views.IssueStatisticsView.as_view(), name='statistics'),
    
    # Refactoring
    path('refactor/', self_refactor_views.AutoRefactorView.as_view(), name='refactor'),
    path('refactor-directory/', self_refactor_views.RefactorDirectoryView.as_view(), name='refactor-directory'),
    path('history/', self_refactor_views.SelfRefactoringHistoryView.as_view(), name='history'),
    
    # Reports & Recommendations
    path('report/', self_refactor_views.QualityReportView.as_view(), name='report'),
    path('recommendations/', self_refactor_views.RecommendationsView.as_view(), name='recommendations'),
]
