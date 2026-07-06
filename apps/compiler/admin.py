from django.contrib import admin
from apps.compiler.models import CodeSnippet, ExecutionHistory, CodeLike


@admin.register(CodeSnippet)
class CodeSnippetAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'is_public', 'likes', 'views', 'created_at']
    search_fields = ['title', 'user__username']
    list_filter = ['is_public', 'created_at']


@admin.register(ExecutionHistory)
class ExecutionHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'execution_time', 'created_at']
    search_fields = ['user__username']
    list_filter = ['status', 'created_at']


@admin.register(CodeLike)
class CodeLikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'code_snippet', 'created_at']
    search_fields = ['user__username', 'code_snippet__title']
