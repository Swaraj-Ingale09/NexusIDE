from rest_framework import serializers
from .models import (
    Problem, TestCase, ProblemSubmission, UserProblemStats,
    Contest, ContestParticipation, ProblemCategory
)


class ProblemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemCategory
        fields = ('id', 'name', 'slug', 'description', 'icon')


class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ('id', 'input_data', 'expected_output', 'explanation', 'is_sample')
        extra_kwargs = {
            'expected_output': {'required': False}  # Hidden for non-sample cases
        }


class ProblemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    test_cases = TestCaseSerializer(many=True, read_only=True)
    
    class Meta:
        model = Problem
        fields = (
            'id', 'title', 'slug', 'description', 'difficulty', 'category',
            'category_name', 'tags', 'time_limit', 'memory_limit', 'status',
            'views', 'submissions', 'accepted_submissions', 'acceptance_rate',
            'test_cases', 'created_at'
        )
        read_only_fields = ('views', 'submissions', 'accepted_submissions', 'acceptance_rate')


class ProblemDetailSerializer(ProblemSerializer):
    """Detailed problem view with explanation"""
    class Meta:
        model = Problem
        fields = ProblemSerializer.Meta.fields + ('explanation', 'updated_at', 'published_at')


class ProblemSubmissionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    problem_title = serializers.CharField(source='problem.title', read_only=True)
    
    class Meta:
        model = ProblemSubmission
        fields = (
            'id', 'user', 'user_name', 'problem', 'problem_title', 'code',
            'status', 'passed_tests', 'total_tests', 'execution_time',
            'memory_used', 'error_message', 'submitted_at', 'judged_at'
        )
        read_only_fields = (
            'status', 'passed_tests', 'total_tests', 'execution_time',
            'memory_used', 'error_message', 'submitted_at', 'judged_at'
        )


class UserProblemStatsSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserProblemStats
        fields = (
            'user', 'username', 'problems_solved', 'problems_attempted',
            'total_submissions', 'total_accepted', 'easy_solved',
            'medium_solved', 'hard_solved', 'expert_solved',
            'best_acceptance_rate', 'average_solve_time'
        )


class ContestSerializer(serializers.ModelSerializer):
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    problem_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Contest
        fields = (
            'id', 'title', 'description', 'creator', 'creator_name',
            'start_time', 'end_time', 'duration', 'status', 'is_public',
            'max_participants', 'problem_count', 'participants', 'submissions',
            'created_at'
        )
        read_only_fields = ('created_at', 'participants', 'submissions')
    
    def get_problem_count(self, obj):
        return obj.problems.count()


class ContestParticipationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = ContestParticipation
        fields = (
            'id', 'user', 'username', 'contest', 'problems_solved',
            'total_score', 'rank', 'penalty_time', 'registered_at',
            'started_at', 'finished_at'
        )
        read_only_fields = ('registered_at', 'started_at', 'finished_at')
