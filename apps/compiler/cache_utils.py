"""
Safe cache utilities that gracefully handle Redis/cache failures
"""

import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SafeCache:
    """
    Safe cache wrapper that continues gracefully if cache is unavailable
    """
    
    @staticmethod
    def get(key, default=None):
        """
        Safely get from cache, return default if cache fails
        """
        try:
            return cache.get(key, default)
        except Exception as e:
            logger.warning(f"Cache get failed for key '{key}': {type(e).__name__}")
            return default
    
    @staticmethod
    def set(key, value, timeout=300):
        """
        Safely set cache, continue if cache fails
        """
        try:
            cache.set(key, value, timeout)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for key '{key}': {type(e).__name__}")
            return False
    
    @staticmethod
    def get_or_set(key, func, timeout=300):
        """
        Safely get or set cache using callable
        """
        try:
            return cache.get_or_set(key, func, timeout)
        except Exception as e:
            logger.warning(f"Cache get_or_set failed for key '{key}': {type(e).__name__}")
            # If cache fails, just call the function
            try:
                return func()
            except Exception as func_error:
                logger.error(f"Function execution also failed: {func_error}")
                return None
    
    @staticmethod
    def delete(key):
        """
        Safely delete from cache
        """
        try:
            cache.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for key '{key}': {type(e).__name__}")
            return False
    
    @staticmethod
    def clear():
        """
        Safely clear cache
        """
        try:
            cache.clear()
            return True
        except Exception as e:
            logger.warning(f"Cache clear failed: {type(e).__name__}")
            return False
