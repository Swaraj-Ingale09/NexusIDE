"""
AI Query Caching System
Stores all AI queries/responses in database for reuse and analytics
"""

import hashlib
import logging
from typing import Dict, Optional, Tuple
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class AIQueryCache:
    """Manages AI query caching and lookup"""
    
    CACHE_DURATION = 30 * 24 * 60 * 60  # 30 days
    
    @staticmethod
    def get_hash(query_input: str, action: str) -> str:
        """Generate hash for query for deduplication"""
        combined = f"{action}:{query_input.strip().lower()}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    @staticmethod
    def normalize_query(query_input: str) -> str:
        """Normalize query for better matching"""
        # Remove extra whitespace and convert to lowercase
        return ' '.join(query_input.strip().lower().split())
    
    @staticmethod
    def get_similar_responses(query_input: str, action: str, limit: int = 3) -> list:
        """
        Get similar cached responses for a query
        
        Args:
            query_input: The code or prompt
            action: The action type (fix, explain, optimize, etc)
            limit: Number of similar responses to return
        
        Returns:
            List of similar cached queries
        """
        from apps.compiler.models import AIQuery
        
        try:
            query_hash = AIQueryCache.get_hash(query_input, action)
            
            # First try exact match
            exact_match = AIQuery.objects.filter(
                query_hash=query_hash,
                action=action,
                status='success'
            ).order_by('-reuse_count', '-created_at').first()
            
            if exact_match:
                logger.info(f"Cache HIT (exact): {action}")
                exact_match.increment_reuse()
                return [exact_match]
            
            # If no exact match, try similar queries with same action
            similar = list(AIQuery.objects.filter(
                action=action,
                status='success'
            ).exclude(
                response_output__exact=''
            ).order_by('-reuse_count', '-created_at')[:limit])
            
            if similar:
                logger.info(f"Cache HIT (similar): {action} - {len(similar)} results")
                return similar
            
            logger.info(f"Cache MISS: {action}")
            return []
        
        except Exception as e:
            logger.error(f"Cache lookup error: {e}")
            return []
    
    @staticmethod
    def save_query(
        user,
        action: str,
        query_input: str,
        response_output: str,
        provider: str = 'openrouter',
        status: str = 'success',
        execution_time: float = 0,
        model_name: str = '',
        tokens_used: int = 0,
        error_message: str = '',
        code_snippet=None
    ) -> 'AIQuery':
        """
        Save AI query and response to database
        
        Args:
            user: Django User object
            action: Action type (fix, explain, optimize, etc)
            query_input: The input code or prompt
            response_output: The AI response
            provider: Which AI provider (openrouter, nvidia, fallback)
            status: success, failed, or partial
            execution_time: Time taken in seconds
            model_name: Name of the model used
            tokens_used: Number of tokens consumed
            error_message: Error message if failed
            code_snippet: Related CodeSnippet object
        
        Returns:
            Saved AIQuery object
        """
        from apps.compiler.models import AIQuery
        
        try:
            query_hash = AIQueryCache.get_hash(query_input, action)
            
            ai_query = AIQuery.objects.create(
                user=user,
                action=action,
                query_input=query_input,
                query_hash=query_hash,
                response_output=response_output,
                provider=provider,
                status=status,
                execution_time=execution_time,
                model_name=model_name,
                tokens_used=tokens_used,
                error_message=error_message,
                code_snippet=code_snippet
            )
            
            logger.info(f"Query saved: {user.username if user else 'anon'} - {action}")
            return ai_query
        
        except Exception as e:
            logger.error(f"Error saving query: {e}")
            return None
    
    @staticmethod
    def get_user_statistics(user) -> Dict:
        """Get AI usage statistics for a user"""
        from apps.compiler.models import AIQuery
        
        try:
            queries = AIQuery.objects.filter(user=user)
            
            stats = queries.aggregate(
                total_execution_time=Sum('execution_time'),
                total_tokens_used=Sum('tokens_used'),
            )
            stats = queries.aggregate(
                total_execution_time=Sum('execution_time'),
                total_tokens_used=Sum('tokens_used'),
                total_queries=Count('id'),
                successful_queries=Count('id', filter=Q(status='success')),
                failed_queries=Count('id', filter=Q(status='failed')),
            )
            most_used_action = queries.values('action').annotate(
                count=Count('id')
            ).order_by('-count').first()
            most_used_provider = queries.values('provider').annotate(
                count=Count('id')
            ).order_by('-count').first()

            return {
                'total_queries': stats.get('total_queries') or 0,
                'successful_queries': stats.get('successful_queries') or 0,
                'failed_queries': stats.get('failed_queries') or 0,
                'total_execution_time': stats.get('total_execution_time') or 0,
                'total_tokens_used': stats.get('total_tokens_used') or 0,
                'most_used_action': most_used_action,
                'most_used_provider': most_used_provider,
            }
        
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    @staticmethod
    def get_popular_queries(limit: int = 10) -> list:
        """Get most popular/reused queries across all users"""
        from apps.compiler.models import AIQuery
        
        try:
            return AIQuery.objects.filter(
                status='success'
            ).order_by('-reuse_count', '-created_at')[:limit]
        
        except Exception as e:
            logger.error(f"Error getting popular queries: {e}")
            return []
    
    @staticmethod
    def cleanup_expired_cache():
        """Remove expired cache entries (optional - run as periodic task)"""
        from apps.compiler.models import AIQuery
        
        try:
            cutoff_date = timezone.now() - timedelta(days=AIQueryCache.CACHE_DURATION)
            deleted_count, _ = AIQuery.objects.filter(
                created_at__lt=cutoff_date
            ).delete()
            
            logger.info(f"Cleaned up {deleted_count} expired cache entries")
            return deleted_count
        
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")
            return 0


class CacheDecorator:
    """Decorator to automatically cache AI responses"""
    
    @staticmethod
    def cache_response(action_type: str):
        """
        Decorator to cache AI function responses
        
        Usage:
        @CacheDecorator.cache_response('fix')
        def fix_code(code, error):
            # AI logic
            return result
        """
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                # Call original function
                result = func(self, *args, **kwargs)
                
                # Cache the result
                try:
                    user = kwargs.get('user') or getattr(self, 'user', None)
                    query_input = args[0] if args else ''
                    
                    if result and query_input:
                        AIQueryCache.save_query(
                            user=user,
                            action=action_type,
                            query_input=query_input,
                            response_output=result.get('generated_code') or result.get('explanation') or str(result),
                            provider=result.get('provider', 'unknown'),
                            status='success' if result.get('success') else 'failed'
                        )
                except Exception as e:
                    logger.error(f"Error caching response: {e}")
                
                return result
            
            return wrapper
        return decorator
