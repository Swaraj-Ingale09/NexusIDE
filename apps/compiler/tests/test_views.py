import pytest
from rest_framework import status
from apps.compiler.models import CodeSnippet, ExecutionHistory


@pytest.mark.django_db
class TestCodeSnippetViewSet:
    def test_create_snippet(self, auth_client):
        response = auth_client.post('/api/code/', {
            'title': 'Test Snippet',
            'code': 'print("hello")',
            'language': 'python',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert CodeSnippet.objects.filter(title='Test Snippet').exists()

    def test_list_snippets(self, auth_client, user):
        CodeSnippet.objects.create(user=user, title='S1', code='c', language='python')
        response = auth_client.get('/api/code/')
        assert response.status_code == status.HTTP_200_OK

    def test_snippet_like_toggle(self, auth_client, user):
        snippet = CodeSnippet.objects.create(user=user, title='S1', code='c', language='python')
        response = auth_client.post(f'/api/code/{snippet.id}/like/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['liked'] is True

        response = auth_client.post(f'/api/code/{snippet.id}/like/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['liked'] is False

    def test_snippet_unauthenticated(self, client):
        response = client.get('/api/code/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestExecutionHistory:
    def test_list_history(self, auth_client, user):
        ExecutionHistory.objects.create(user=user, code='c', output='o', status='success')
        response = auth_client.get('/api/history/')
        assert response.status_code == status.HTTP_200_OK

    def test_history_unauthenticated(self, client):
        response = client.get('/api/history/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestExecuteCode:
    def test_execute_requires_auth(self, client):
        response = client.post('/api/execute/', {
            'code': 'print("hello")',
            'language': 'python',
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_execute_python(self, auth_client):
        response = auth_client.post('/api/execute/', {
            'code': 'print("hello world")',
            'language': 'python',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert 'hello world' in response.data.get('output', '')

    def test_execute_code_too_large(self, auth_client):
        response = auth_client.post('/api/execute/', {
            'code': 'x' * 2000000,
            'language': 'python',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAIAssistant:
    def test_ai_requires_auth(self, client):
        response = client.post('/api/ai/', {
            'code': 'print("hello")',
            'action': 'explain',
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
