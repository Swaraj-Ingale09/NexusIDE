from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import (
    Problem, TestCase, ProblemSubmission, UserProblemStats,
    Contest, ContestParticipation, ProblemCategory, ProblemAttempt
)
from .serializers import (
    ProblemSerializer, ProblemDetailSerializer, ProblemSubmissionSerializer,
    UserProblemStatsSerializer, ContestSerializer, ContestParticipationSerializer,
    ProblemCategorySerializer
)
from .judge import evaluate_submission
from .leaderboard import LeaderboardManager, AchievementManager
from config.rate_limiter import rate_limit, SUBMISSION_LIMITER, get_client_identifier


class ProblemCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Problem categories"""
    queryset = ProblemCategory.objects.all()
    serializer_class = ProblemCategorySerializer
    permission_classes = [AllowAny]


class ProblemViewSet(viewsets.ReadOnlyModelViewSet):
    """Problems listing and detail"""
    serializer_class = ProblemSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Problem.objects.filter(status='published')
        
        # Filtering
        difficulty = self.request.query_params.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProblemDetailSerializer
        return ProblemSerializer
    
    @action(detail=True, methods=['get'])
    def test_cases(self, request, pk=None):
        """Get test cases for a problem"""
        problem = self.get_object()
        if request.user.is_authenticated:
            test_cases = problem.test_cases.filter(is_sample=True)
        else:
            test_cases = problem.test_cases.filter(is_sample=True)
        
        from apps.problems.serializers import TestCaseSerializer
        serializer = TestCaseSerializer(test_cases, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def user_attempt(self, request, pk=None):
        """Get user's attempt on this problem"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        problem = self.get_object()
        try:
            attempt = ProblemAttempt.objects.get(
                user=request.user,
                problem=problem
            )
            return Response({
                'is_solved': attempt.is_solved,
                'attempts': attempt.attempts,
                'best_time': attempt.best_execution_time,
            })
        except ProblemAttempt.DoesNotExist:
            return Response({
                'is_solved': False,
                'attempts': 0,
                'best_time': None,
            })


class ProblemSubmissionView(APIView):
    """Submit code solution"""
    permission_classes = [AllowAny]

    def post(self, request):
        """Submit a solution"""
        identifier = get_client_identifier(request)
        if not SUBMISSION_LIMITER.is_allowed(identifier):
            return Response(
                {'error': 'Rate limit exceeded', 'message': 'Too many submissions. Try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        try:
            problem_id = request.data.get('problem_id')
            code = request.data.get('code', '').strip()
            
            if not problem_id or not code:
                return Response(
                    {'error': 'problem_id and code are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            problem = get_object_or_404(Problem, id=problem_id, status='published')
            
            language = request.data.get('language', 'python').lower().strip()
            if language not in ('python', 'c', 'cpp', 'c++'):
                return Response(
                    {'error': f"Language '{language}' not supported. Available: python, c, cpp"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if language == 'c++':
                language = 'cpp'
            
            # Create submission
            submission = ProblemSubmission.objects.create(
                user=request.user if request.user.is_authenticated else None,
                problem=problem,
                code=code,
                language=language,
            )
            
            # Evaluate (synchronously for now, should be Celery task in production)
            evaluate_submission(submission)
            
            serializer = ProblemSubmissionSerializer(submission)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Problem submission failed")
            return Response(
                {'error': 'Submission failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserStatsView(APIView):
    """Get user's problem-solving statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id=None):
        """Get user stats"""
        if user_id:
            user_id = user_id
        else:
            user_id = request.user.id
        
        try:
            stats = UserProblemStats.objects.get(user_id=user_id)
            serializer = UserProblemStatsSerializer(stats)
            return Response(serializer.data)
        except UserProblemStats.DoesNotExist:
            return Response(
                {'error': 'Stats not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class LeaderboardView(APIView):
    """Leaderboard endpoints"""
    permission_classes = [AllowAny]
    
    def get(self, request, leaderboard_type='global'):
        """Get leaderboard"""
        limit = min(int(request.query_params.get('limit', 100)), 500)
        offset = int(request.query_params.get('offset', 0))
        
        if leaderboard_type == 'global':
            leaderboard = LeaderboardManager.get_global_leaderboard(limit, offset)
        elif leaderboard_type == 'weekly':
            leaderboard = LeaderboardManager.get_weekly_leaderboard(limit, offset)
        elif leaderboard_type == 'monthly':
            leaderboard = LeaderboardManager.get_monthly_leaderboard(limit, offset)
        elif leaderboard_type == 'problems':
            leaderboard = LeaderboardManager.get_problem_solving_leaderboard(limit)
        else:
            return Response(
                {'error': 'Invalid leaderboard type'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({'leaderboard': leaderboard})


class UserRankView(APIView):
    """Get user rank in leaderboard"""
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        """Get user's rank"""
        leaderboard_type = request.query_params.get('type', 'global')
        rank_info = LeaderboardManager.get_user_rank(user_id, leaderboard_type)
        return Response(rank_info)


class ContestViewSet(viewsets.ModelViewSet):
    """Contests"""
    serializer_class = ContestSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Contest.objects.filter(
            Q(is_public=True) | Q(creator=self.request.user)
        )
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-start_time')
    
    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        """Register for a contest"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        contest = self.get_object()
        
        # Check if already registered
        if ContestParticipation.objects.filter(
            user=request.user,
            contest=contest
        ).exists():
            return Response(
                {'message': 'Already registered'},
                status=status.HTTP_200_OK
            )
        
        participation = ContestParticipation.objects.create(
            user=request.user,
            contest=contest
        )
        
        serializer = ContestParticipationSerializer(participation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def leaderboard(self, request, pk=None):
        """Get contest leaderboard"""
        contest = self.get_object()
        leaderboard = LeaderboardManager.get_contest_leaderboard(contest.id)
        return Response({'leaderboard': leaderboard})


class AchievementView(APIView):
    """User achievements"""
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        """Get user achievements"""
        achievements = AchievementManager.get_user_achievements(user_id)
        next_achievement = AchievementManager.get_next_achievement(user_id)
        
        return Response({
            'achievements': achievements,
            'next_achievement': next_achievement
        })
