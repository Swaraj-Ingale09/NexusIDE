from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'categories', views.ProblemCategoryViewSet, basename='category')
router.register(r'problems', views.ProblemViewSet, basename='problem')
router.register(r'contests', views.ContestViewSet, basename='contest')

urlpatterns = [
    path('', include(router.urls)),
    path('submit/', views.ProblemSubmissionView.as_view(), name='submit'),
    path('stats/<int:user_id>/', views.UserStatsView.as_view(), name='user-stats'),
    path('leaderboard/<str:leaderboard_type>/', views.LeaderboardView.as_view(), name='leaderboard'),
    path('rank/<int:user_id>/', views.UserRankView.as_view(), name='user-rank'),
    path('achievements/<int:user_id>/', views.AchievementView.as_view(), name='achievements'),
]
