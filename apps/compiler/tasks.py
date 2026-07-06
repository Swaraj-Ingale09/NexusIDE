"""
Shared tasks for NexusIDE maintenance.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_api_keys():
    """
    Periodic task to clean up expired API keys.
    Scheduled via CELERY_BEAT_SCHEDULE in settings.
    """
    from config.api_key_rotation import get_key_rotation

    rotation = get_key_rotation()
    removed = rotation.cleanup_expired_keys()
    logger.info("API key cleanup: removed %d expired keys", removed)
    return {'removed': removed}


@shared_task
def cleanup_old_heartbeats():
    """Periodic task to clean up heartbeats older than 30 days."""
    from apps.users.models import UserHeartbeat
    cutoff = timezone.now() - timezone.timedelta(days=30)
    deleted, _ = UserHeartbeat.objects.filter(timestamp__lt=cutoff).delete()
    logger.info("Cleaned up %d old heartbeat records", deleted)
    return {'deleted': deleted}


@shared_task
def cleanup_old_executions():
    """Periodic task to clean up execution history older than 7 days."""
    from apps.compiler.models import ExecutionHistory
    cutoff = timezone.now() - timezone.timedelta(days=7)
    deleted, _ = ExecutionHistory.objects.filter(created_at__lt=cutoff).delete()
    logger.info("Cleaned up %d old execution history records", deleted)
    return {'deleted': deleted}
