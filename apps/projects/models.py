from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Project(models.Model):
    PROJECT_TYPE_CHOICES = [
        ('basic', 'Basic Python'),
        ('django', 'Django Project'),
        ('fastapi', 'FastAPI Project'),
        ('data_science', 'Data Science'),
        ('ml', 'Machine Learning'),
        ('automation', 'Automation'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    project_type = models.CharField(max_length=50, choices=PROJECT_TYPE_CHOICES, default='basic')
    is_public = models.BooleanField(default=False)
    likes = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    tags = models.CharField(max_length=500, blank=True)
    thumbnail = models.ImageField(upload_to='projects/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'projects'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_public', '-likes']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class ProjectFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    name = models.CharField(max_length=255)
    content = models.TextField()
    file_type = models.CharField(max_length=20, default='py')
    is_main = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['project', 'name']
        db_table = 'project_files'

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class ProjectDependency(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='dependencies')
    package_name = models.CharField(max_length=100)
    version = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ['project', 'package_name']
        db_table = 'project_dependencies'

    def __str__(self):
        return f"{self.project.name} - {self.package_name}"


class ProjectComment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'project_comments'

    def __str__(self):
        return f"{self.user.username} - {self.project.name}"
