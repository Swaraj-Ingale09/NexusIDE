"""
Notification system: model, views, and WebSocket consumer for real-time updates.
"""
import json
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


class Notification(models.Model):
    """User notification model."""
    TYPE_CHOICES = [
        ('system', 'System'),
        ('achievement', 'Achievement'),
        ('comment', 'Comment'),
        ('like', 'Like'),
        ('follow', 'Follow'),
        ('mention', 'Mention'),
        ('submission', 'Submission'),
        ('security', 'Security'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    def mark_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])

    def __str__(self):
        return f"[{self.notification_type}] {self.title} -> {self.user.username}"

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]


class NotificationViewSet(viewsets.ModelViewSet):
    """REST API for notifications."""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page_size = int(request.query_params.get('page_size', 20))
        page = int(request.query_params.get('page', 1))
        offset = (page - 1) * page_size
        total = qs.count()
        notifications = qs[offset:offset + page_size]
        return Response({
            'results': [
                {
                    'id': n.id,
                    'type': n.notification_type,
                    'title': n.title,
                    'message': n.message,
                    'link': n.link,
                    'read': n.is_read,
                    'created_at': n.created_at.isoformat(),
                    'metadata': n.metadata,
                }
                for n in notifications
            ],
            'count': total,
            'unread_count': qs.filter(is_read=False).count(),
        })

    @action(detail=False, methods=['post'], url_path='mark-read')
    def mark_read(self, request, *args, **kwargs):
        notif_id = request.data.get('id')
        if notif_id:
            try:
                n = Notification.objects.get(id=notif_id, user=request.user)
                n.mark_read()
                return Response({'ok': True})
            except Notification.DoesNotExist:
                return Response({'error': 'Not found'}, status=404)
        return Response({'error': 'id required'}, status=400)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request, *args, **kwargs):
        now = timezone.now()
        Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True, read_at=now)
        return Response({'ok': True})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request, *args, **kwargs):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'count': count})


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications per user."""

    async def connect(self):
        if self.scope['user'] == AnonymousUser():
            await self.close()
            return

        self.user_id = self.scope['user'].id
        self.room_group_name = f'notifications_{self.user_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        unread = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'init',
            'unread_count': unread,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', '')

        if msg_type == 'mark_read':
            notif_id = data.get('id')
            if notif_id:
                await self.mark_notification_read(notif_id)
                unread = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': unread,
                }))
        elif msg_type == 'mark_all_read':
            await self.mark_all_read()
            await self.send(text_data=json.dumps({
                'type': 'unread_count',
                'count': 0,
            }))

    async def notification_send(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'id': event['id'],
            'title': event['title'],
            'message': event['message'],
            'notification_type': event['notification_type'],
            'link': event.get('link', ''),
            'created_at': event['created_at'],
        }))

    async def notification_unread_count(self, event):
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count'],
        }))

    @database_sync_to_async
    def get_unread_count(self):
        return Notification.objects.filter(user_id=self.user_id, is_read=False).count()

    @database_sync_to_async
    def mark_notification_read(self, notif_id):
        try:
            n = Notification.objects.get(id=notif_id, user_id=self.user_id)
            n.mark_read()
        except Notification.DoesNotExist:
            pass

    @database_sync_to_async
    def mark_all_read(self):
        now = timezone.now()
        Notification.objects.filter(
            user_id=self.user_id, is_read=False
        ).update(is_read=True, read_at=now)


def create_notification(user, notification_type, title, message, link='', metadata=None):
    """Helper to create a notification and send it via WebSocket."""
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    notif = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
        metadata=metadata or {},
    )

    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user.id}',
            {
                'type': 'notification_send',
                'id': notif.id,
                'title': title,
                'message': message,
                'notification_type': notification_type,
                'link': link,
                'created_at': notif.created_at.isoformat(),
            }
        )

    return notif
