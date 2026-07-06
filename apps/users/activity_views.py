"""
Realistic Activity Tracking Views - Only REAL data, no padding
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Q, Avg, Sum
from datetime import timedelta

from .models import (
    UserActivity, UserHeartbeat, UserProfile,
    UserSession, UserSatisfaction
)
from .analytics import RealisticAnalytics, ActivityTracker
from apps.compiler.models import AIQuery, ExecutionHistory, CodeSnippet
from apps.problems.models import ProblemSubmission


class RealisticUserStatsView(APIView):
    """Get REAL user statistics - no padding, only actual tracked data"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get comprehensive real stats for the logged-in user"""
        user = request.user
        days = int(request.query_params.get('days', 30))
        
        try:
            stats = {
                'user': {
                    'username': user.username,
                    'email': user.email,
                    'joined': user.date_joined.isoformat(),
                },
                'time_spent': RealisticAnalytics.get_real_time_spent(user, days),
                'api_usage': RealisticAnalytics.get_real_api_usage(user, days),
                'code_executions': RealisticAnalytics.get_real_code_executions(user, days),
                'ai_usage': RealisticAnalytics.get_real_ai_usage(user, days),
                'sessions': RealisticAnalytics.get_real_sessions(user, days),
                'activities': RealisticAnalytics.get_real_activity_summary(user, days),
            }
            
            return Response(stats, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RealisticDashboardView(APIView):
    """Admin dashboard with ONLY REAL, actual data - no padding or fake metrics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get realistic dashboard data"""
        
        # Check admin privileges
        if not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'error': 'Admin privileges required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        days = int(request.query_params.get('days', 30))
        
        try:
            dashboard_data = RealisticAnalytics.get_realistic_dashboard_data(days)
            return Response(dashboard_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ActivityLogView(APIView):
    """View and filter real user activities"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get activity log for user or all users (if admin)"""
        
        days = int(request.query_params.get('days', 30))
        activity_type = request.query_params.get('type', None)
        limit = int(request.query_params.get('limit', 100))
        
        cutoff = timezone.now() - timedelta(days=days)
        
        # Non-admins can only see their own activities
        if not request.user.is_staff:
            activities = UserActivity.objects.filter(
                user=request.user,
                timestamp__gte=cutoff
            )
        else:
            activities = UserActivity.objects.filter(
                timestamp__gte=cutoff
            )
        
        # Filter by activity type if specified
        if activity_type:
            activities = activities.filter(activity_type=activity_type)
        
        # Get activity breakdown
        breakdown = activities.values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get recent activities
        recent = activities.values(
            'user__username', 'activity_type', 'description', 'timestamp'
        ).order_by('-timestamp')[:limit]
        
        return Response({
            'total_activities': activities.count(),
            'breakdown': list(breakdown),
            'recent': list(recent),
        }, status=status.HTTP_200_OK)


class CodeExecutionTrackingView(APIView):
    """Track actual code execution and log metrics"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Track a code execution event"""
        
        user = request.user
        language = request.data.get('language', 'unknown')
        execution_time = float(request.data.get('execution_time', 0))
        status_code = request.data.get('status', 'unknown')
        error_message = request.data.get('error', '')
        
        try:
            # Log the activity
            ActivityTracker.track_code_execution(
                user, language, execution_time, status_code, error_message
            )
            
            # Get updated stats
            stats = RealisticAnalytics.get_real_code_executions(user, days=30)
            
            return Response({
                'success': True,
                'message': 'Execution tracked',
                'current_stats': stats
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AIUsageTrackingView(APIView):
    """Track actual AI usage and log metrics"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Track an AI usage event"""
        
        user = request.user
        action = request.data.get('action', 'unknown')
        tokens = int(request.data.get('tokens', 0))
        response_time = float(request.data.get('response_time', 0))
        provider = request.data.get('provider', 'unknown')
        
        try:
            # Log the activity
            ActivityTracker.track_ai_usage(user, action, tokens, response_time)
            
            # Get updated stats
            stats = RealisticAnalytics.get_real_ai_usage(user, days=30)
            
            return Response({
                'success': True,
                'message': 'AI usage tracked',
                'tokens_used': tokens,
                'response_time': response_time,
                'current_stats': stats
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
