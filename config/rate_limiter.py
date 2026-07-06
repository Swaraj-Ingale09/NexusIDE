"""
Rate limiting middleware and utilities
Protects against abuse and DDoS attacks
"""

from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded"""
    pass


class RateLimiter:
    """
    Rate limiting utility
    Supports per-user, per-IP, and global limits
    """

    def __init__(self, key_prefix: str, max_requests: int, time_window: int):
        """
        Args:
            key_prefix: Cache key prefix
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
        """
        self.key_prefix = key_prefix
        self.max_requests = max_requests
        self.time_window = time_window

    def _get_counter_key(self, identifier: str) -> str:
        return f"{self.key_prefix}:{identifier}"

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed using atomic cache operations."""
        counter_key = self._get_counter_key(identifier)

        try:
            count = cache.get(counter_key)
            if count is None:
                cache.set(counter_key, 1, self.time_window)
                return 1 <= self.max_requests
            count = cache.incr(counter_key)
            return count <= self.max_requests
        except Exception as e:
            logger.warning(f"Cache error in rate limiter: {e}")
            return True

    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests in current window."""
        counter_key = self._get_counter_key(identifier)
        try:
            current_count = cache.get(counter_key, 0)
            return max(0, self.max_requests - current_count)
        except Exception:
            return self.max_requests

    def get_seconds_until_reset(self, identifier: str) -> int:
        """Get seconds until the current window resets (TTL of the cache key)."""
        counter_key = self._get_counter_key(identifier)
        try:
            ttl = cache.ttl(counter_key)
            if ttl is None or ttl < 0:
                return self.time_window
            return ttl
        except Exception:
            return self.time_window


EXECUTION_LIMITER = RateLimiter(
    key_prefix="execution",
    max_requests=10,
    time_window=60
)

LOGIN_LIMITER = RateLimiter(
    key_prefix="login",
    max_requests=5,
    time_window=300
)

API_LIMITER = RateLimiter(
    key_prefix="api",
    max_requests=100,
    time_window=3600
)

SUBMISSION_LIMITER = RateLimiter(
    key_prefix="submission",
    max_requests=50,
    time_window=3600
)

AI_LIMITER = RateLimiter(
    key_prefix="ai",
    max_requests=50,        # 50 AI requests per user per hour
    time_window=3600        # 1 hour window
)

# Per-feature AI limits: 3 uses per feature per hour
AI_FEATURE_LIMITS = {
    'explain':    RateLimiter(key_prefix="ai:explain",    max_requests=3, time_window=3600),
    'fix':        RateLimiter(key_prefix="ai:fix",        max_requests=3, time_window=3600),
    'optimize':   RateLimiter(key_prefix="ai:optimize",   max_requests=3, time_window=3600),
    'debug':      RateLimiter(key_prefix="ai:debug",      max_requests=3, time_window=3600),
    'format':     RateLimiter(key_prefix="ai:format",     max_requests=3, time_window=3600),
    'test':       RateLimiter(key_prefix="ai:test",       max_requests=3, time_window=3600),
    'chat':       RateLimiter(key_prefix="ai:chat",       max_requests=3, time_window=3600),
    'suggest':    RateLimiter(key_prefix="ai:suggest",    max_requests=3, time_window=3600),
    'generate':   RateLimiter(key_prefix="ai:generate",   max_requests=3, time_window=3600),
    'review':     RateLimiter(key_prefix="ai:review",     max_requests=3, time_window=3600),
    'refactor':   RateLimiter(key_prefix="ai:refactor",   max_requests=3, time_window=3600),
    'complete':   RateLimiter(key_prefix="ai:complete",   max_requests=3, time_window=3600),
    'bug_diagnosis': RateLimiter(key_prefix="ai:bug_diagnosis", max_requests=3, time_window=3600),
    'documentation': RateLimiter(key_prefix="ai:documentation", max_requests=3, time_window=3600),
    'architecture':  RateLimiter(key_prefix="ai:architecture",  max_requests=3, time_window=3600),
    'general_help':  RateLimiter(key_prefix="ai:general_help",  max_requests=3, time_window=3600),
}

# Default fallback for unknown actions
AI_DEFAULT_LIMITER = RateLimiter(key_prefix="ai:default", max_requests=3, time_window=3600)


def get_client_identifier(request) -> str:
    """
    Get unique identifier for rate limiting
    Prefers user ID, falls back to IP address
    """
    if request.user.is_authenticated:
        return f"user:{request.user.id}"

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', 'unknown')

    return f"ip:{ip}"


def rate_limit(limiter: RateLimiter, identifier_func=None):
    """
    Decorator for rate limiting views

    Usage:
        @rate_limit(EXECUTION_LIMITER)
        def execute_code(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if identifier_func:
                identifier = identifier_func(request)
            else:
                identifier = get_client_identifier(request)

            if not limiter.is_allowed(identifier):
                remaining = limiter.get_remaining(identifier)
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Try again later.',
                    'retry_after': limiter.time_window,
                    'remaining': remaining,
                }, status=429)

            response = view_func(request, *args, **kwargs)
            remaining = limiter.get_remaining(identifier)

            if hasattr(response, 'data') and isinstance(response.data, dict):
                response.data['remaining_requests'] = remaining
            elif hasattr(response, 'content'):
                pass

            return response

        return wrapper
    return decorator


class RateLimitMiddleware:
    """
    Middleware for global rate limiting
    Protects API endpoints from abuse
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/'):
            identifier = get_client_identifier(request)

            path = request.path
            if '/execute/' in path or '/compile/' in path or '/terminal/' in path:
                limiter = EXECUTION_LIMITER
            elif '/submit' in path or '/problems/' in path:
                limiter = SUBMISSION_LIMITER
            else:
                limiter = API_LIMITER

            if not limiter.is_allowed(identifier):
                logger.warning(f"Rate limit exceeded for {identifier} on {request.path}")
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.',
                    'retry_after': limiter.time_window,
                }, status=429)

        response = self.get_response(request)
        return response


class BruteForceProtection:
    """
    Specific protection against brute force attacks
    """

    FAILED_LOGIN_KEY = "failed_login:{}"
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION = 900

    @classmethod
    def record_failed_login(cls, identifier: str) -> bool:
        """
        Record a failed login attempt
        Returns True if account should be locked
        """
        cache_key = cls.FAILED_LOGIN_KEY.format(identifier)

        try:
            failed_count = cache.get(cache_key)
            if failed_count is None:
                cache.set(cache_key, 1, cls.LOCKOUT_DURATION)
                return 1 >= cls.MAX_FAILED_ATTEMPTS
            failed_count = cache.incr(cache_key)
            return failed_count >= cls.MAX_FAILED_ATTEMPTS
        except Exception:
            return False

    @classmethod
    def record_successful_login(cls, identifier: str):
        """Clear failed login attempts on success"""
        cache_key = cls.FAILED_LOGIN_KEY.format(identifier)
        try:
            cache.delete(cache_key)
        except Exception:
            pass

    @classmethod
    def is_locked(cls, identifier: str) -> bool:
        """Check if account is locked"""
        cache_key = cls.FAILED_LOGIN_KEY.format(identifier)
        try:
            failed_count = cache.get(cache_key, 0)
            return failed_count >= cls.MAX_FAILED_ATTEMPTS
        except Exception:
            return False

    @classmethod
    def get_lockout_time_remaining(cls, identifier: str) -> int:
        """Check if account is currently locked out"""
        cache_key = cls.FAILED_LOGIN_KEY.format(identifier)
        try:
            failed_count = cache.get(cache_key, 0)
            if failed_count >= cls.MAX_FAILED_ATTEMPTS:
                return cls.LOCKOUT_DURATION
            return 0
        except Exception:
            return 0


def require_rate_limit_check(view_func):
    """
    Decorator to add rate limit checking to a view
    Automatically uses appropriate limiter based on request path
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        identifier = get_client_identifier(request)

        path = request.path
        if 'execute' in path or 'compile' in path or 'terminal' in path:
            limiter = EXECUTION_LIMITER
        elif 'submit' in path or 'problems' in path:
            limiter = SUBMISSION_LIMITER
        elif 'login' in path:
            limiter = LOGIN_LIMITER
        else:
            limiter = API_LIMITER

        if not limiter.is_allowed(identifier):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
                'retry_after': limiter.time_window,
                'remaining': 0,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        return view_func(request, *args, **kwargs)

    return wrapper
