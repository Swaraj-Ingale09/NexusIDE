import json
import pytest
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.contrib.auth.models import AnonymousUser

from apps.compiler.consumers import ExecutionConsumer, AIStreamConsumer


@database_sync_to_async
def create_user(username='wsuser', password='wspass123'):
    return User.objects.create_user(username=username, password=password)


from django.contrib.auth.models import User


@pytest.mark.asyncio
@pytest.mark.django_db
class TestExecutionConsumer:
    async def test_anonymous_user_rejected(self):
        communicator = WebsocketCommunicator(
            ExecutionConsumer.as_asgi(),
            '/ws/execution/1/'
        )
        communicator.scope['user'] = AnonymousUser()
        communicator.scope['url_route'] = {'kwargs': {'execution_id': '1'}}
        connected, _ = await communicator.connect()
        assert not connected

    async def test_authenticated_user_connects(self):
        user = await create_user('execuser1')
        communicator = WebsocketCommunicator(
            ExecutionConsumer.as_asgi(),
            '/ws/execution/42/'
        )
        communicator.scope['user'] = user
        communicator.scope['url_route'] = {'kwargs': {'execution_id': '42'}}
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_receive_input_sends_to_group(self):
        user = await create_user('execuser2')
        channel_layer = get_channel_layer()

        communicator = WebsocketCommunicator(
            ExecutionConsumer.as_asgi(),
            '/ws/execution/1/'
        )
        communicator.scope['user'] = user
        communicator.scope['url_route'] = {'kwargs': {'execution_id': '1'}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({'type': 'input', 'content': 'hello'})
        await communicator.disconnect()

    async def test_execution_output_message(self):
        user = await create_user('execuser3')
        channel_layer = get_channel_layer()

        communicator = WebsocketCommunicator(
            ExecutionConsumer.as_asgi(),
            '/ws/execution/1/'
        )
        communicator.scope['user'] = user
        communicator.scope['url_route'] = {'kwargs': {'execution_id': '1'}}
        connected, _ = await communicator.connect()
        assert connected

        await channel_layer.group_send(
            'execution_1',
            {
                'type': 'execution_output',
                'content': 'Hello World',
                'line_number': 1,
            }
        )

        response = await communicator.receive_json_from(timeout=5)
        assert response['type'] == 'output'
        assert response['content'] == 'Hello World'
        assert response['line_number'] == 1

        await communicator.disconnect()

    async def test_execution_error_message(self):
        user = await create_user('execuser4')
        channel_layer = get_channel_layer()

        communicator = WebsocketCommunicator(
            ExecutionConsumer.as_asgi(),
            '/ws/execution/1/'
        )
        communicator.scope['user'] = user
        communicator.scope['url_route'] = {'kwargs': {'execution_id': '1'}}
        connected, _ = await communicator.connect()
        assert connected

        await channel_layer.group_send(
            'execution_1',
            {
                'type': 'execution_error',
                'content': 'RuntimeError: something broke',
            }
        )

        response = await communicator.receive_json_from(timeout=5)
        assert response['type'] == 'error'
        assert 'RuntimeError' in response['content']

        await communicator.disconnect()

    async def test_execution_complete_message(self):
        user = await create_user('execuser5')
        channel_layer = get_channel_layer()

        communicator = WebsocketCommunicator(
            ExecutionConsumer.as_asgi(),
            '/ws/execution/1/'
        )
        communicator.scope['user'] = user
        communicator.scope['url_route'] = {'kwargs': {'execution_id': '1'}}
        connected, _ = await communicator.connect()
        assert connected

        await channel_layer.group_send(
            'execution_1',
            {
                'type': 'execution_complete',
                'status': 'success',
                'execution_time': 1.23,
                'total_lines': 10,
            }
        )

        response = await communicator.receive_json_from(timeout=5)
        assert response['type'] == 'completed'
        assert response['status'] == 'success'
        assert response['execution_time'] == 1.23

        await communicator.disconnect()

    async def test_disconnect_closes_connection(self):
        user = await create_user('execuser6')

        communicator = WebsocketCommunicator(
            ExecutionConsumer.as_asgi(),
            '/ws/execution/1/'
        )
        communicator.scope['user'] = user
        communicator.scope['url_route'] = {'kwargs': {'execution_id': '1'}}
        connected, _ = await communicator.connect()
        assert connected

        await communicator.disconnect()
        assert communicator.output_queue.empty()


@pytest.mark.asyncio
@pytest.mark.django_db
class TestAIStreamConsumer:
    async def test_anonymous_user_rejected(self):
        communicator = WebsocketCommunicator(
            AIStreamConsumer.as_asgi(),
            '/ws/ai-stream/'
        )
        communicator.scope['user'] = AnonymousUser()
        connected, _ = await communicator.connect()
        assert not connected

    async def test_authenticated_user_connects(self):
        user = await create_user('aiuser1')
        communicator = WebsocketCommunicator(
            AIStreamConsumer.as_asgi(),
            '/ws/ai-stream/'
        )
        communicator.scope['user'] = user
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_ai_chunk_message(self):
        user = await create_user('aiuser2')
        channel_layer = get_channel_layer()

        communicator = WebsocketCommunicator(
            AIStreamConsumer.as_asgi(),
            '/ws/ai-stream/'
        )
        communicator.scope['user'] = user
        connected, _ = await communicator.connect()
        assert connected

        room_group = f'ai_{user.id}'
        await channel_layer.group_send(
            room_group,
            {
                'type': 'ai_chunk',
                'content': 'Here is an explanation...',
            }
        )

        response = await communicator.receive_json_from(timeout=5)
        assert response['type'] == 'chunk'
        assert response['content'] == 'Here is an explanation...'

        await communicator.disconnect()

    async def test_ai_complete_message(self):
        user = await create_user('aiuser3')
        channel_layer = get_channel_layer()

        communicator = WebsocketCommunicator(
            AIStreamConsumer.as_asgi(),
            '/ws/ai-stream/'
        )
        communicator.scope['user'] = user
        connected, _ = await communicator.connect()
        assert connected

        room_group = f'ai_{user.id}'
        await channel_layer.group_send(
            room_group,
            {
                'type': 'ai_complete',
                'response': 'Full AI response here',
                'provider': 'openrouter',
            }
        )

        response = await communicator.receive_json_from(timeout=5)
        assert response['type'] == 'completed'
        assert response['response'] == 'Full AI response here'
        assert response['provider'] == 'openrouter'

        await communicator.disconnect()

    async def test_ai_error_message(self):
        user = await create_user('aiuser4')
        channel_layer = get_channel_layer()

        communicator = WebsocketCommunicator(
            AIStreamConsumer.as_asgi(),
            '/ws/ai-stream/'
        )
        communicator.scope['user'] = user
        connected, _ = await communicator.connect()
        assert connected

        room_group = f'ai_{user.id}'
        await channel_layer.group_send(
            room_group,
            {
                'type': 'ai_error',
                'error': 'Rate limit exceeded',
            }
        )

        response = await communicator.receive_json_from(timeout=5)
        assert response['type'] == 'error'
        assert response['error'] == 'Rate limit exceeded'

        await communicator.disconnect()

    async def test_disconnect_closes_connection(self):
        user = await create_user('aiuser5')

        communicator = WebsocketCommunicator(
            AIStreamConsumer.as_asgi(),
            '/ws/ai-stream/'
        )
        communicator.scope['user'] = user
        connected, _ = await communicator.connect()
        assert connected

        await communicator.disconnect()
        assert communicator.output_queue.empty()
