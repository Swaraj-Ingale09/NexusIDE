from rest_framework import serializers
from apps.projects.models import Project, ProjectFile, ProjectDependency, ProjectComment


class ProjectFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectFile
        fields = ['id', 'name', 'content', 'file_type', 'is_main', 'created_at', 'updated_at']


class ProjectDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDependency
        fields = ['id', 'package_name', 'version']


class ProjectCommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = ProjectComment
        fields = ['id', 'user', 'content', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    files = ProjectFileSerializer(read_only=True, many=True)
    dependencies = ProjectDependencySerializer(read_only=True, many=True)
    comments = ProjectCommentSerializer(read_only=True, many=True)

    class Meta:
        model = Project
        fields = ['id', 'user', 'name', 'description', 'project_type', 'is_public',
                  'likes', 'views', 'tags', 'thumbnail', 'files', 'dependencies', 'comments',
                  'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at', 'likes', 'views']
