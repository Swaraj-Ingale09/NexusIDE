import pytest
from rest_framework import status
from apps.problems.models import Problem, TestCase, ProblemCategory


@pytest.mark.django_db
class TestProblemEndpoints:
    def test_list_problems(self, client):
        response = client.get('/api/problems/problems/')
        assert response.status_code == status.HTTP_200_OK

    def test_list_categories(self, client):
        response = client.get('/api/problems/categories/')
        assert response.status_code == status.HTTP_200_OK

    def test_problem_detail(self, client):
        category = ProblemCategory.objects.create(name='Arrays', description='Array problems')
        problem = Problem.objects.create(
            title='Two Sum',
            description='Find two numbers that add up to target',
            difficulty=1,
            category=category,
            status='published',
        )
        response = client.get(f'/api/problems/problems/{problem.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_submit_requires_problem(self, client):
        response = client.post('/api/problems/submit/', {
            'code': 'print("hello")',
            'language': 'python',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_submit_requires_code(self, client):
        response = client.post('/api/problems/submit/', {
            'problem_id': 999,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_leaderboard(self, client):
        response = client.get('/api/problems/leaderboard/global/')
        assert response.status_code == status.HTTP_200_OK
