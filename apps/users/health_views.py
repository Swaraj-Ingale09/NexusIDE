"""
Health check and system status endpoints.
"""
import time
from datetime import datetime

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt


@method_decorator(csrf_exempt, name='dispatch')
class HealthCheckView(View):
    """
    System health check endpoint.
    Returns status of database, cache, and system components.
    """
    
    def get(self, request):
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {}
        }
        
        # Database check
        try:
            start = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_time = (time.time() - start) * 1000
            
            db_engine = settings.DATABASES['default']['ENGINE'].split('.')[-1]
            db_info = {
                'status': 'healthy',
                'response_time_ms': round(db_time, 2),
                'engine': db_engine,
            }
            
            # Add PostgreSQL-specific info
            if 'postgresql' in settings.DATABASES['default']['ENGINE']:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    db_info['version'] = cursor.fetchone()[0]
                    cursor.execute("SELECT current_database()")
                    db_info['database'] = cursor.fetchone()[0]
            
            health['checks']['database'] = db_info
        except Exception as e:
            health['checks']['database'] = {
                'status': 'unhealthy',
                'error': 'Database check failed.',
            }
            health['status'] = 'degraded'
        
        # Cache check
        try:
            from django.core.cache import cache
            start = time.time()
            cache.set('health_check', 'ok', 10)
            cache.get('health_check')
            cache_time = (time.time() - start) * 1000
            health['checks']['cache'] = {
                'status': 'healthy',
                'response_time_ms': round(cache_time, 2),
                'backend': settings.CACHES['default']['BACKEND'].split('.')[-1],
            }
        except Exception as e:
            health['checks']['cache'] = {
                'status': 'unhealthy',
                'error': 'Cache check failed.',
            }
            health['status'] = 'degraded'
        
        # Disk space check
        try:
            import os
            if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                db_path = settings.DATABASES['default']['NAME']
                stat = os.statvfs(db_path)
                free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
                total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            else:
                # For PostgreSQL, check the data directory
                with connection.cursor() as cursor:
                    cursor.execute("SHOW data_directory")
                    data_dir = cursor.fetchone()[0]
                stat = os.statvfs(data_dir)
                free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
                total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            
            used_pct = ((total_gb - free_gb) / total_gb) * 100 if total_gb > 0 else 0
            
            health['checks']['disk'] = {
                'status': 'healthy' if free_gb > 1 else 'warning',
                'free_gb': round(free_gb, 2),
                'total_gb': round(total_gb, 2),
                'used_percent': round(used_pct, 1),
            }
            if free_gb < 1:
                health['status'] = 'degraded'
        except Exception as e:
            health['checks']['disk'] = {
                'status': 'unknown',
                'error': 'Disk check failed.',
            }
        
        # System info
        health['system'] = {
            'debug': settings.DEBUG,
            'allowed_hosts': len(settings.ALLOWED_HOSTS),
            'installed_apps': len(settings.INSTALLED_APPS),
        }
        
        status_code = 200 if health['status'] == 'healthy' else 503
        return JsonResponse(health, status=status_code)


@method_decorator(csrf_exempt, name='dispatch')
class DatabaseStatsView(View):
    """
    Database statistics endpoint (admin only).
    Returns row counts and table sizes.
    """
    
    def get(self, request):
        # Check admin access
        if not request.user.is_authenticated or request.user.username != settings.MASTER_ADMIN_USERNAME:
            return JsonResponse({'error': 'Admin access required'}, status=403)
        
        stats = {
            'tables': {},
            'total_rows': 0,
        }
        
        try:
            with connection.cursor() as cursor:
                # Get all tables
                if 'sqlite' in settings.DATABASES['default']['ENGINE']:
                    cursor.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                        ORDER BY name
                    """)
                else:
                    cursor.execute("""
                        SELECT tablename FROM pg_tables 
                        WHERE schemaname = 'public'
                        ORDER BY tablename
                    """)
                
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    try:
                        cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                        count = cursor.fetchone()[0]
                        stats['tables'][table] = count
                        stats['total_rows'] += count
                    except Exception:
                        stats['tables'][table] = 'error'
        
        except Exception:
            stats['error'] = 'Failed to retrieve database stats.'
        
        return JsonResponse(stats)
