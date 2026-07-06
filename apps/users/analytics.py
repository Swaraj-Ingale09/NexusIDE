"""
Real Analytics Tracking System - Logs ONLY actual user activity, no padding
"""
from django.utils import timezone
from django.db.models import Count, Q, Avg, Sum, F
from django.db import models
from datetime import timedelta
import logging
from .models import (
    UserActivity, UserHeartbeat, UserSession, 
    UserProfile, AdminLog, UserSatisfaction
)
from apps.compiler.models import AIQuery, ExecutionHistory, CodeSnippet
from apps.problems.models import ProblemSubmission

logger = logging.getLogger(__name__)


class RealisticAnalytics:
    """Track ONLY real, actual metrics - no padding or fake data"""
    
    @staticmethod
    def log_activity(user, activity_type, description=""):
        """Log actual user activity with real timestamp"""
        UserActivity.objects.create(
            user=user,
            activity_type=activity_type,
            description=description,
            timestamp=timezone.now()
        )
    
    @staticmethod
    def log_heartbeat(user, page=""):
        """Log user presence - called when user sends heartbeat"""
        UserHeartbeat.objects.create(
            user=user,
            timestamp=timezone.now(),
            page=page,
            is_active=True
        )
    
    @staticmethod
    def get_real_time_spent(user, days=30):
        """Calculate REAL time spent based on heartbeats (1 heartbeat = 1 minute)"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        heartbeat_count = UserHeartbeat.objects.filter(
            user=user,
            timestamp__gte=cutoff_date,
            is_active=True
        ).count()
        
        # 1 heartbeat = 1 minute of active time
        total_seconds = heartbeat_count * 60
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        return {
            'total_seconds': total_seconds,
            'formatted': f"{hours}h {minutes}m",
            'heartbeats': heartbeat_count
        }
    
    @staticmethod
    def get_real_api_usage(user, days=30):
        """Count REAL API calls made by user"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        api_calls = {
            'ai_queries': AIQuery.objects.filter(
                user=user,
                created_at__gte=cutoff_date
            ).count(),
            'code_executions': ExecutionHistory.objects.filter(
                user=user,
                created_at__gte=cutoff_date
            ).count(),
            'problem_submissions': ProblemSubmission.objects.filter(
                user=user,
                submitted_at__gte=cutoff_date
            ).count(),
            'activity_logs': UserActivity.objects.filter(
                user=user,
                timestamp__gte=cutoff_date
            ).count(),
        }
        
        api_calls['total'] = sum(api_calls.values())
        return api_calls
    
    @staticmethod
    def get_real_code_executions(user, days=30):
        """Get REAL code execution statistics"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        executions = ExecutionHistory.objects.filter(
            user=user,
            created_at__gte=cutoff_date
        )
        
        stats = executions.aggregate(
            total=Count('id'),
            successful=Count('id', filter=Q(status='success')),
            failed=Count('id', filter=Q(status='error')),
            avg_time=Avg('execution_time'),
            total_time=Sum('execution_time')
        )
        
        success_rate = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        return {
            'total': stats['total'],
            'successful': stats['successful'],
            'failed': stats['failed'],
            'success_rate': round(success_rate, 2),
            'avg_execution_time': round(stats['avg_time'] or 0, 3),
            'total_execution_time': stats['total_time'] or 0,
        }
    
    @staticmethod
    def get_real_ai_usage(user, days=30):
        """Get REAL AI usage statistics"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        ai_queries = AIQuery.objects.filter(
            user=user,
            created_at__gte=cutoff_date
        )
        
        stats = ai_queries.aggregate(
            total_queries=Count('id'),
            total_tokens=Sum('tokens_used'),
            successful=Count('id', filter=Q(status='success')),
            failed=Count('id', filter=Q(status='error')),
            avg_response_time=Avg('execution_time')
        )
        
        success_rate = (stats['successful'] / stats['total_queries'] * 100) if stats['total_queries'] > 0 else 0
        
        # Group by provider
        by_provider = ai_queries.values('provider').annotate(
            count=Count('id'),
            tokens=Sum('tokens_used')
        )
        
        return {
            'total_queries': stats['total_queries'],
            'total_tokens': stats['total_tokens'] or 0,
            'successful': stats['successful'],
            'failed': stats['failed'],
            'success_rate': round(success_rate, 2),
            'avg_response_time': round(stats['avg_response_time'] or 0, 3),
            'by_provider': {item['provider']: {
                'count': item['count'],
                'tokens': item['tokens']
            } for item in by_provider}
        }
    
    @staticmethod
    def get_real_sessions(user, days=30):
        """Get REAL session statistics"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        sessions = UserSession.objects.filter(
            user=user,
            login_time__gte=cutoff_date
        )
        
        total_duration = 0
        for session in sessions:
            total_duration += session.get_session_duration()
        
        avg_duration = (total_duration / sessions.count()) if sessions.count() > 0 else 0
        
        return {
            'total_sessions': sessions.count(),
            'total_duration_seconds': int(total_duration),
            'avg_session_duration_seconds': int(avg_duration),
            'first_login': sessions.first().login_time if sessions.exists() else None,
            'last_login': sessions.last().login_time if sessions.exists() else None,
        }
    
    @staticmethod
    def get_real_activity_summary(user, days=30):
        """Get REAL activity summary - actual activities performed"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        activities = UserActivity.objects.filter(
            user=user,
            timestamp__gte=cutoff_date
        ).values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        activity_summary = {}
        total_activities = 0
        
        for activity in activities:
            activity_type = activity['activity_type']
            count = activity['count']
            activity_summary[activity_type] = count
            total_activities += count
        
        return {
            'by_type': activity_summary,
            'total': total_activities
        }
    
    @staticmethod
    def get_realistic_dashboard_data(days=30):
        """Get REAL dashboard data - only actual metrics, no padding"""
        from django.contrib.auth.models import User
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Real active users (those with recent heartbeats)
        active_users = UserHeartbeat.objects.filter(
            timestamp__gte=cutoff_date
        ).values('user').distinct().count()
        
        # Real total users
        total_users = User.objects.count()
        
        # Real active sessions (not logout yet or within last 24 hours)
        active_sessions = UserSession.objects.filter(
            logout_time__isnull=True
        ).count() + UserSession.objects.filter(
            logout_time__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        # Real total activities
        total_activities = UserActivity.objects.filter(
            timestamp__gte=cutoff_date
        ).count()
        
        # REAL total time spent - calculated from SESSIONS, not heartbeats
        # This is the actual login to logout time for all users
        all_sessions = UserSession.objects.filter(
            login_time__gte=cutoff_date
        )
        total_session_duration = 0
        session_count = 0
        
        try:
            for session in all_sessions:
                if session.logout_time:
                    # Only count completed sessions (with logout time)
                    duration = (session.logout_time - session.login_time).total_seconds()
                    total_session_duration += duration
                    session_count += 1
                else:
                    # For ongoing sessions, calculate from login to now
                    duration = (timezone.now() - session.login_time).total_seconds()
                    total_session_duration += duration
                    session_count += 1
        except Exception as e:
            logger.error(f"Error calculating session duration: {e}")
        
        # Convert total seconds to hours and minutes
        total_hours = int(total_session_duration // 3600)
        total_minutes = int((total_session_duration % 3600) // 60)
        
        # Calculate average session time
        avg_session_seconds = 0
        if session_count > 0:
            avg_session_seconds = total_session_duration / session_count
        
        # Format as minutes:seconds
        avg_session_minutes = int(avg_session_seconds // 60)
        avg_session_secs = int(avg_session_seconds % 60)
        avg_session_str = f"{avg_session_minutes}m {avg_session_secs}s"
        
        # Real code executions
        try:
            total_executions = ExecutionHistory.objects.filter(
                created_at__gte=cutoff_date
            ).aggregate(
                total=Count('id'),
                successful=Count('id', filter=Q(status='success')),
                total_time=Sum('execution_time')
            )
        except Exception as e:
            logger.error(f"Error getting executions: {e}")
            total_executions = {'total': 0, 'successful': 0, 'total_time': 0}
        
        # Real AI queries
        try:
            total_ai_queries = AIQuery.objects.filter(
                created_at__gte=cutoff_date
            ).aggregate(
                total=Count('id'),
                tokens=Sum('tokens_used')
            )
        except Exception as e:
            logger.error(f"Error getting AI queries: {e}")
            total_ai_queries = {'total': 0, 'tokens': 0}
        
        # Real code snippets
        try:
            total_snippets = CodeSnippet.objects.count()
        except Exception as e:
            logger.error(f"Error getting snippets: {e}")
            total_snippets = 0
        
        # Real problem stats
        try:
            total_submissions = ProblemSubmission.objects.filter(
                submitted_at__gte=cutoff_date
            ).count()
            
            successful_submissions = ProblemSubmission.objects.filter(
                submitted_at__gte=cutoff_date,
                status='accepted'
            ).count()
        except Exception as e:
            logger.error(f"Error getting problem stats: {e}")
            total_submissions = 0
            successful_submissions = 0
        
        return {
            'summary': {
                'total_users': total_users,
                'active_users': active_users,
                'active_sessions': active_sessions,
                'total_activities': total_activities,
                'avg_session_duration': avg_session_str,
                'total_time_spent': f"{total_hours}h {total_minutes}m",
                'total_sessions': session_count,
            },
            'code_stats': {
                'total_executions': total_executions.get('total', 0) or 0,
                'successful_executions': total_executions.get('successful', 0) or 0,
                'total_execution_time': total_executions.get('total_time', 0) or 0,
                'total_snippets': total_snippets,
            },
            'ai_stats': {
                'total_queries': total_ai_queries.get('total', 0) or 0,
                'total_tokens': total_ai_queries.get('tokens', 0) or 0,
            },
            'problem_stats': {
                'total_submissions': total_submissions,
                'successful_submissions': successful_submissions,
                'success_rate': round(
                    (successful_submissions / total_submissions * 100) if total_submissions > 0 else 0,
                    2
                )
            },
        }


class ActivityTracker:
    """Simple wrapper to track activities from views"""
    
    @staticmethod
    def track_code_execution(user, language, execution_time, status, error_message=""):
        """Track when user executes code"""
        RealisticAnalytics.log_activity(
            user,
            'compile',
            f"Executed {language} code in {execution_time}s - {status}"
        )
    
    @staticmethod
    def track_ai_usage(user, action, tokens, response_time):
        """Track when user uses AI"""
        RealisticAnalytics.log_activity(
            user,
            'ai_chat',
            f"AI {action} - {tokens} tokens, {response_time}s response time"
        )
    
    @staticmethod
    def track_snippet_creation(user, language, lines):
        """Track when user creates snippet"""
        RealisticAnalytics.log_activity(
            user,
            'snippet_create',
            f"Created {language} snippet with {lines} lines"
        )
    
    @staticmethod
    def track_page_view(user, page):
        """Track page views"""
        RealisticAnalytics.log_activity(
            user,
            'page_view',
            f"Viewed {page}"
        )
