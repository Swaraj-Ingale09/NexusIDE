"""
Database Query Optimizations
Use prefetch_related and select_related to avoid N+1 queries
"""

from django.db.models import Prefetch, Q, Count, Avg, Sum
from django.contrib.auth.models import User
from apps.users.models import UserProfile, UserSession, UserActivity, UserHeartbeat

def get_users_with_stats(limit=100):
    """Get all users with their stats - optimized for minimal queries"""
    return User.objects.prefetch_related(
        'profile',
        'sessions',
        'activities',
        'heartbeats'
    ).all()[:limit]

def get_user_dashboard_data(user):
    """Get user dashboard data efficiently"""
    heartbeats = UserHeartbeat.objects.filter(user=user).count()
    activities = UserActivity.objects.filter(user=user).count()
    
    return {
        'active_time': heartbeats * 60,  # in seconds
        'total_activities': activities,
        'profile': user.profile if hasattr(user, 'profile') else None
    }

def get_admin_dashboard_stats_optimized():
    """Get admin dashboard stats with minimal database queries"""
    
    # Use aggregation to avoid N+1 queries
    user_stats = User.objects.aggregate(
        total_count=Count('id'),
    )
    
    heartbeat_stats = UserHeartbeat.objects.aggregate(
        total=Count('id'),
        unique_users=Count('user', distinct=True)
    )
    
    activity_stats = UserActivity.objects.aggregate(
        total=Count('id'),
    )
    
    profile_stats = UserProfile.objects.aggregate(
        avg_quality=Avg('code_quality_score'),
        total_tokens=Sum('total_ai_tokens_used'),
        total_executions=Sum('total_code_executions'),
    )
    
    return {
        'total_users': user_stats['total_count'],
        'active_users': heartbeat_stats['unique_users'],
        'total_heartbeats': heartbeat_stats['total'],
        'total_activities': activity_stats['total'],
        'avg_code_quality': profile_stats['avg_quality'] or 0.0,
        'total_ai_tokens': profile_stats['total_tokens'] or 0,
        'total_executions': profile_stats['total_executions'] or 0,
    }

def get_recent_activities(limit=20):
    """Get recent activities efficiently"""
    return UserActivity.objects.select_related('user').order_by('-timestamp')[:limit]

def batch_create_heartbeats(user_ids, page):
    """Batch create heartbeats to reduce database hits"""
    heartbeats = [
        UserHeartbeat(user_id=user_id, page=page)
        for user_id in user_ids
    ]
    UserHeartbeat.objects.bulk_create(heartbeats, batch_size=100)

def get_user_with_related(user_id):
    """Get user with all related data in minimal queries"""
    return User.objects.select_related('profile').prefetch_related(
        'sessions',
        'activities',
        'heartbeats',
        'satisfaction_ratings'
    ).get(id=user_id)

# Cache decorator for expensive queries
from functools import wraps
from django.core.cache import cache
import hashlib

def cache_result(timeout=300):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{hashlib.md5(str((args, kwargs)).encode()).hexdigest()}"
            result = cache.get(key)
            
            if result is None:
                result = func(*args, **kwargs)
                cache.set(key, result, timeout)
            
            return result
        return wrapper
    return decorator

@cache_result(timeout=300)
def get_dashboard_stats_cached():
    """Get dashboard stats with 5-minute caching"""
    return get_admin_dashboard_stats_optimized()
