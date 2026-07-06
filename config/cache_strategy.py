"""
Caching strategy for NexusIDE.
Provides decorators and utilities for caching frequently accessed data.
"""
import hashlib
import functools
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class CacheStrategy:
    """Centralized cache management with TTL and invalidation."""

    # Cache timeouts (in seconds)
    TIMEOUTS = {
        'user_profile': 300,      # 5 minutes
        'user_stats': 60,         # 1 minute
        'community_feed': 30,     # 30 seconds
        'problem_list': 120,      # 2 minutes
        'leaderboard': 60,        # 1 minute
        'snippets_list': 30,      # 30 seconds
        'ai_suggestions': 600,    # 10 minutes
        'code_analysis': 300,     # 5 minutes
        'admin_metrics': 30,      # 30 seconds
        'system_health': 10,      # 10 seconds
    }

    @classmethod
    def get_timeout(cls, key_type: str) -> int:
        """Get timeout for a cache key type."""
        return cls.TIMEOUTS.get(key_type, 60)

    @classmethod
    def make_key(cls, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix and arguments."""
        key_parts = [prefix]
        for arg in args:
            key_parts.append(str(arg))
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ':'.join(key_parts)

    @classmethod
    def invalidate_pattern(cls, pattern: str):
        """Invalidate all keys matching a pattern."""
        try:
            # For Redis, use delete pattern
            if hasattr(cache._cache, '_client'):
                keys = cache._cache._client.keys(f"*{pattern}*")
                if keys:
                    cache._cache._client.delete(*keys)
            else:
                # For LocMem, we can't efficiently invalidate by pattern
                logger.debug(f"Pattern invalidation not supported for this cache backend: {pattern}")
        except Exception as e:
            logger.warning(f"Cache pattern invalidation failed: {e}")


def cache_result(key_type: str, key_prefix: str, timeout: int = None):
    """
    Decorator to cache function results.
    
    Usage:
        @cache_result('user_profile', 'user:{user_id}')
        def get_user_profile(user_id):
            return UserProfile.objects.get(user_id=user_id)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            cache_key = CacheStrategy.make_key(key_prefix, *args, **kwargs)

            # Try to get from cache
            try:
                cached = cache.get(cache_key)
                if cached is not None:
                    return cached
            except Exception as e:
                logger.warning(f"Cache get failed: {e}")

            # Compute result
            result = func(*args, **kwargs)

            # Store in cache
            try:
                ttl = timeout or CacheStrategy.get_timeout(key_type)
                cache.set(cache_key, result, ttl)
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")

            return result
        return wrapper
    return decorator


def invalidate_cache(key_prefix: str, *args, **kwargs):
    """Invalidate a specific cache entry."""
    cache_key = CacheStrategy.make_key(key_prefix, *args, **kwargs)
    try:
        cache.delete(cache_key)
    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")


def cache_page_response(timeout: int = 60, key_prefix: str = 'page'):
    """
    Decorator to cache entire page responses.
    More aggressive than Django's cache_page - works with DRF.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Skip caching for authenticated users (personalized content)
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            # Build cache key from request path and query params
            cache_key = CacheStrategy.make_key(
                key_prefix,
                request.path,
                str(sorted(request.GET.items()))
            )

            # Try to get from cache
            try:
                cached = cache.get(cache_key)
                if cached is not None:
                    return cached
            except Exception:
                pass

            # Generate response
            response = view_func(request, *args, **kwargs)

            # Cache successful responses
            if hasattr(response, 'status_code') and response.status_code == 200:
                try:
                    cache.set(cache_key, response, timeout)
                except Exception:
                    pass

            return response
        return wrapper
    return decorator


# ── Predefined cache operations for common patterns ──

class UserCache:
    """Cache operations for user-related data."""

    @staticmethod
    @cache_result('user_profile', 'profile:{user_id}')
    def get_profile(user_id):
        from apps.users.models import UserProfile
        return UserProfile.objects.select_related('user').get(user_id=user_id)

    @staticmethod
    def invalidate_profile(user_id):
        invalidate_cache('profile', user_id)

    @staticmethod
    @cache_result('user_stats', 'stats:{user_id}')
    def get_stats(user_id):
        from apps.users.models import UserProfile
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            return {
                'xp_points': profile.xp_points,
                'level': profile.level,
                'problems_solved': profile.problems_solved,
                'total_code_executions': profile.total_code_executions,
                'total_snippets_created': profile.total_snippets_created,
            }
        except UserProfile.DoesNotExist:
            return None

    @staticmethod
    def invalidate_stats(user_id):
        invalidate_cache('stats', user_id)


class CommunityCache:
    """Cache operations for community data."""

    @staticmethod
    @cache_result('community_feed', 'feed:{page}:{category}')
    def get_feed(page=1, category=None):
        from apps.community.models import CommunityPost
        queryset = CommunityPost.objects.select_related('user').prefetch_related('comments__user')
        if category:
            queryset = queryset.filter(category=category)
        return list(queryset.order_by('-created_at')[:20])

    @staticmethod
    def invalidate_feed():
        CacheStrategy.invalidate_pattern('feed:')


class ProblemCache:
    """Cache operations for problems."""

    @staticmethod
    @cache_result('problem_list', 'problems:{difficulty}:{category}')
    def get_list(difficulty=None, category=None):
        from apps.problems.models import Problem
        queryset = Problem.objects.all()
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        if category:
            queryset = queryset.filter(category=category)
        return list(queryset.values('id', 'title', 'difficulty', 'category', 'submissions_count'))

    @staticmethod
    def invalidate_list():
        CacheStrategy.invalidate_pattern('problems:')


class AdminCache:
    """Cache operations for admin dashboard."""

    @staticmethod
    @cache_result('admin_metrics', 'admin:metrics')
    def get_metrics():
        from django.contrib.auth.models import User
        from apps.users.models import UserActivity, UserSession
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(weeks=1)

        return {
            'total_users': User.objects.count(),
            'active_today': UserActivity.objects.filter(timestamp__gte=day_ago).values('user').distinct().count(),
            'active_week': UserActivity.objects.filter(timestamp__gte=week_ago).values('user').distinct().count(),
            'total_sessions': UserSession.objects.count(),
            'online_now': UserSession.objects.filter(
                logout_time__isnull=True,
                login_time__gte=now - timedelta(hours=1)
            ).count(),
        }

    @staticmethod
    def invalidate_metrics():
        invalidate_cache('admin', 'metrics')
