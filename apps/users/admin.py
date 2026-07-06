from django.contrib import admin
from apps.users.models import UserProfile, Achievement, UserSession, UserActivity, UserSatisfaction, AdminLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'xp_points', 'level', 'problems_solved']
    search_fields = ['user__username']


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'earned_at']
    search_fields = ['user__user__username']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'login_time', 'logout_time', 'get_session_duration_formatted']
    search_fields = ['user__username']
    list_filter = ['login_time']
    readonly_fields = ['login_time', 'logout_time', 'get_session_duration_formatted']


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'timestamp']
    search_fields = ['user__username']
    list_filter = ['activity_type', 'timestamp']
    readonly_fields = ['timestamp']


@admin.register(UserSatisfaction)
class UserSatisfactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'rating', 'would_recommend', 'submitted_at']
    search_fields = ['user__username']
    list_filter = ['rating', 'would_recommend', 'submitted_at']
    readonly_fields = ['submitted_at']


@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    list_display = ['admin_user', 'action', 'timestamp']
    search_fields = ['admin_user__username']
    list_filter = ['timestamp']
    readonly_fields = ['timestamp']
