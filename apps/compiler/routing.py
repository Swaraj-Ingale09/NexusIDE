from django.urls import re_path
from apps.compiler import consumers
from apps.users.notification_views import NotificationConsumer

websocket_urlpatterns = [
    re_path(r'ws/execution/(?P<execution_id>\d+)/$', consumers.ExecutionConsumer.as_asgi()),
    re_path(r'ws/ai-stream/$', consumers.AIStreamConsumer.as_asgi()),
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
]
