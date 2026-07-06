import pytest
from rest_framework import status
from apps.projects.models import Project, ProjectFile


@pytest.mark.django_db
class TestProjectViewSet:
    def test_create_project(self, auth_client):
        response = auth_client.post('/api/projects/', {
            'name': 'Test Project',
            'description': 'A test project',
            'project_type': 'basic',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Project.objects.filter(name='Test Project').exists()

    def test_list_projects(self, auth_client, user):
        Project.objects.create(user=user, name='P1', project_type='basic')
        response = auth_client.get('/api/projects/')
        assert response.status_code == status.HTTP_200_OK

    def test_project_unauthenticated(self, client):
        response = client.get('/api/projects/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestProjectFile:
    def test_add_file(self, auth_client, user):
        project = Project.objects.create(user=user, name='P1', project_type='basic')
        response = auth_client.post(f'/api/projects/{project.id}/add_file/', {
            'name': 'main.py',
            'content': 'print("hello")',
            'file_type': 'python',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert ProjectFile.objects.filter(project=project, name='main.py').exists()
