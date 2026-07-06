import pytest
from rest_framework import status
from apps.community.models import CommunityPost, PostComment, PostLike


@pytest.mark.django_db
class TestCommunityFeed:
    def test_create_post(self, auth_client):
        response = auth_client.post('/api/community/', {
            'title': 'Test Post',
            'content': 'Hello community',
            'category': 'discussion',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert CommunityPost.objects.filter(title='Test Post').exists()

    def test_list_posts(self, auth_client, user):
        CommunityPost.objects.create(user=user, title='P1', content='C1')
        response = auth_client.get('/api/community/')
        assert response.status_code == status.HTTP_200_OK

    def test_like_toggle(self, auth_client, user):
        post = CommunityPost.objects.create(user=user, title='P1', content='C1')
        response = auth_client.post(f'/api/community/{post.id}/like/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['liked'] is True

        response = auth_client.post(f'/api/community/{post.id}/like/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['liked'] is False

    def test_add_comment(self, auth_client, user):
        post = CommunityPost.objects.create(user=user, title='P1', content='C1')
        response = auth_client.post(f'/api/community/{post.id}/add_comment/', {
            'content': 'Great post!',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert PostComment.objects.filter(post=post).exists()

    def test_community_unauthenticated(self, client):
        response = client.get('/api/community/')
        assert response.status_code == status.HTTP_200_OK
