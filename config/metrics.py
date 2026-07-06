"""
Prometheus-compatible metrics endpoint for NexusIDE.
Provides system metrics in a format consumable by Prometheus/Grafana.
"""
import time
import psutil
from django.http import HttpResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings


def metrics_view(request):
    """
    Expose metrics in Prometheus text format.
    GET /metrics/
    """
    lines = []

    # --- Process metrics ---
    process = psutil.Process()
    mem_info = process.memory_info()
    cpu_pct = process.cpu_percent(interval=0.1)

    lines.append('# HELP nexuside_process_cpu_percent Current CPU usage percent')
    lines.append('# TYPE nexuside_process_cpu_percent gauge')
    lines.append(f'nexuside_process_cpu_percent {cpu_pct}')

    lines.append('# HELP nexuside_process_memory_rss_bytes Resident Set Size in bytes')
    lines.append('# TYPE nexuside_process_memory_rss_bytes gauge')
    lines.append(f'nexuside_process_memory_rss_bytes {mem_info.rss}')

    lines.append('# HELP nexuside_process_memory_vms_bytes Virtual Memory Size in bytes')
    lines.append('# TYPE nexuside_process_memory_vms_bytes gauge')
    lines.append(f'nexuside_process_memory_vms_bytes {mem_info.vms}')

    # --- System metrics ---
    sys_mem = psutil.virtual_memory()
    lines.append('# HELP nexuside_system_memory_total_bytes Total system memory')
    lines.append('# TYPE nexuside_system_memory_total_bytes gauge')
    lines.append(f'nexuside_system_memory_total_bytes {sys_mem.total}')

    lines.append('# HELP nexuside_system_memory_available_bytes Available system memory')
    lines.append('# TYPE nexuside_system_memory_available_bytes gauge')
    lines.append(f'nexuside_system_memory_available_bytes {sys_mem.available}')

    lines.append('# HELP nexuside_system_memory_percent Memory usage percent')
    lines.append('# TYPE nexuside_system_memory_percent gauge')
    lines.append(f'nexuside_system_memory_percent {sys_mem.percent}')

    disk = psutil.disk_usage('/')
    lines.append('# HELP nexuside_system_disk_total_bytes Total disk space')
    lines.append('# TYPE nexuside_system_disk_total_bytes gauge')
    lines.append(f'nexuside_system_disk_total_bytes {disk.total}')

    lines.append('# HELP nexuside_system_disk_used_bytes Used disk space')
    lines.append('# TYPE nexuside_system_disk_used_bytes gauge')
    lines.append(f'nexuside_system_disk_used_bytes {disk.used}')

    # --- Database metrics ---
    try:
        start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_latency = (time.time() - start) * 1000

        lines.append('# HELP nexuside_db_latency_ms Database query latency in milliseconds')
        lines.append('# TYPE nexuside_db_latency_ms gauge')
        lines.append(f'nexuside_db_latency_ms {db_latency:.2f}')
        lines.append('# HELP nexuside_db_up Database connectivity (1=up, 0=down)')
        lines.append('# TYPE nexuside_db_up gauge')
        lines.append('nexuside_db_up 1')
    except Exception:
        lines.append('# HELP nexuside_db_up Database connectivity (1=up, 0=down)')
        lines.append('# TYPE nexuside_db_up gauge')
        lines.append('nexuside_db_up 0')

    # --- Cache metrics ---
    try:
        start = time.time()
        cache.set('_metrics_probe', 'ok', 5)
        cache.get('_metrics_probe')
        cache_latency = (time.time() - start) * 1000

        lines.append('# HELP nexuside_cache_latency_ms Cache latency in milliseconds')
        lines.append('# TYPE nexuside_cache_latency_ms gauge')
        lines.append(f'nexuside_cache_latency_ms {cache_latency:.2f}')
        lines.append('# HELP nexuside_cache_up Cache connectivity (1=up, 0=down)')
        lines.append('# TYPE nexuside_cache_up gauge')
        lines.append('nexuside_cache_up 1')
    except Exception:
        lines.append('# HELP nexuside_cache_up Cache connectivity (1=up, 0=down)')
        lines.append('# TYPE nexuside_cache_up gauge')
        lines.append('nexuside_cache_up 0')

    # --- Application info ---
    lines.append('# HELP nexuside_info Application metadata')
    lines.append('# TYPE nexuside_info gauge')
    lines.append(f'nexuside_info{{version="1.0.0",debug="{settings.DEBUG}"}} 1')

    lines.append('# HELP nexuside_uptime_seconds Application uptime in seconds')
    lines.append('# TYPE nexuside_uptime_seconds gauge')
    lines.append(f'nexuside_uptime_seconds {time.time() - process.create_time():.0f}')

    content = '\n'.join(lines) + '\n'
    return HttpResponse(content, content_type='text/plain; charset=utf-8')
