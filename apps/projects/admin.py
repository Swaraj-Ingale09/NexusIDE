from django.contrib import admin
from apps.projects.models import Project, ProjectFile, ProjectDependency, ProjectComment


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'project_type', 'is_public', 'likes', 'views', 'created_at']
    search_fields = ['name', 'user__username']
    list_filter = ['project_type', 'is_public', 'created_at']


@admin.register(ProjectFile)
class ProjectFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'file_type', 'is_main']
    search_fields = ['name', 'project__name']


@admin.register(ProjectDependency)
class ProjectDependencyAdmin(admin.ModelAdmin):
    list_display = ['project', 'package_name', 'version']
    search_fields = ['project__name', 'package_name']


@admin.register(ProjectComment)
class ProjectCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'created_at']
    search_fields = ['user__username', 'project__name']
