import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class ExecutionConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time code execution output streaming."""

    async def connect(self):
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        self.room_group_name = f'execution_{self.execution_id}'

        if self.scope['user'] == AnonymousUser():
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'input')

        if message_type == 'input':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'execution_input',
                    'content': data.get('content', ''),
                }
            )

    async def execution_output(self, event):
        await self.send(text_data=json.dumps({
            'type': 'output',
            'content': event['content'],
            'line_number': event.get('line_number', 0),
        }))

    async def execution_error(self, event):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'content': event['content'],
        }))

    async def execution_complete(self, event):
        await self.send(text_data=json.dumps({
            'type': 'completed',
            'status': event.get('status', 'completed'),
            'execution_time': event.get('execution_time', 0),
            'total_lines': event.get('total_lines', 0),
        }))

    async def execution_input(self, event):
        pass


class AIStreamConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time AI response streaming."""

    async def connect(self):
        if self.scope['user'] == AnonymousUser():
            await self.close()
            return

        self.room_group_name = f'ai_{self.scope["user"].id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action', 'explain')
        code = data.get('code', '')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'ai_request',
                'action': action,
                'code': code,
                'context': data.get('context', ''),
            }
        )

    async def ai_chunk(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chunk',
            'content': event['content'],
        }))

    async def ai_complete(self, event):
        await self.send(text_data=json.dumps({
            'type': 'completed',
            'response': event.get('response', ''),
            'provider': event.get('provider', 'unknown'),
        }))

    async def ai_error(self, event):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'error': event.get('error', 'Unknown error'),
        }))

    async def ai_request(self, event):
        pass
