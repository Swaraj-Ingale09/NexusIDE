from django.contrib import admin
from .models import (
    ProblemCategory, Problem, TestCase, ProblemSubmission,
    UserProblemStats, ProblemAttempt, ProblemRating, Contest,
    ContestParticipation
)


@admin.register(ProblemCategory)
class ProblemCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'category', 'status', 'acceptance_rate')
    list_filter = ('status', 'difficulty', 'category')
    search_fields = ('title', 'description')
    readonly_fields = ('views', 'submissions', 'accepted_submissions')


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('problem', 'order', 'is_sample', 'is_hidden')
    list_filter = ('is_sample', 'is_hidden')


@admin.register(ProblemSubmission)
class ProblemSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'problem', 'status', 'submitted_at')
    list_filter = ('status', 'submitted_at')
    search_fields = ('user__username', 'problem__title')
    readonly_fields = ('passed_tests', 'total_tests', 'execution_time', 'memory_used')


@admin.register(UserProblemStats)
class UserProblemStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'problems_solved', 'total_submissions', 'best_acceptance_rate')
    readonly_fields = ('updated_at',)


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'start_time', 'end_time', 'participants')
    list_filter = ('status', 'start_time')
