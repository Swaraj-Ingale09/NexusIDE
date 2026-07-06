"""
Activity tracking and realistic analytics endpoints
"""
from django.urls import path
from .activity_views import (
    RealisticUserStatsView,
    RealisticDashboardView,
    ActivityLogView,
    CodeExecutionTrackingView,
    AIUsageTrackingView
)

urlpatterns = [
    # User stats - all realistic data
    path('api/user/stats/', RealisticUserStatsView.as_view(), name='user-stats'),
    
    # Dashboard - realistic analytics
    path('api/admin/dashboard/realistic/', RealisticDashboardView.as_view(), name='dashboard-realistic'),
    
    # Activity log
    path('api/activity/log/', ActivityLogView.as_view(), name='activity-log'),
    
    # Track code execution
    path('api/track/execution/', CodeExecutionTrackingView.as_view(), name='track-execution'),
    
    # Track AI usage
    path('api/track/ai-usage/', AIUsageTrackingView.as_view(), name='track-ai-usage'),
]
