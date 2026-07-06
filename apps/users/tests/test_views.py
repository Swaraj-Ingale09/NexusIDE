import pytest
from django.contrib.auth.models import User
from rest_framework import status
from apps.users.models import UserProfile


@pytest.mark.django_db
class TestAuthViewSet:
    def test_register(self, client):
        response = client.post('/api/auth/register/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'strongpass123',
            'password2': 'strongpass123',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert User.objects.filter(username='newuser').exists()

    def test_register_duplicate_username(self, client, user):
        response = client.post('/api/auth/register/', {
            'username': 'testuser',
            'email': 'other@example.com',
            'password': 'strongpass123',
            'password2': 'strongpass123',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login(self, client, user):
        response = client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'access' in response.data

    def test_login_wrong_password(self, client, user):
        response = client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpass',
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout(self, auth_client):
        response = auth_client.post('/api/auth/logout/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestUserProfile:
    def test_get_profile(self, auth_client):
        response = auth_client.get('/api/profile/')
        assert response.status_code == status.HTTP_200_OK
        assert 'bio' in response.data

    def test_update_profile(self, auth_client):
        response = auth_client.put('/api/profile/', {'bio': 'Hello world'})
        assert response.status_code == status.HTTP_200_OK

    def test_profile_unauthenticated(self, client):
        response = client.get('/api/profile/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserStats:
    def test_get_stats(self, auth_client):
        response = auth_client.get('/api/stats/')
        assert response.status_code == status.HTTP_200_OK
        assert 'total_active_seconds' in response.data


@pytest.mark.django_db
class TestUserProfileModel:
    def test_profile_created_on_user_create(self, user):
        assert UserProfile.objects.filter(user=user).exists()

    def test_profile_str(self, user):
        profile = UserProfile.objects.get(user=user)
        assert str(profile) == f"{user.username}'s Profile"
