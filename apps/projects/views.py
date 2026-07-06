import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.db.models import F, Q
from apps.projects.models import Project, ProjectFile, ProjectDependency, ProjectComment
from apps.projects.serializers import ProjectSerializer, ProjectFileSerializer, ProjectDependencySerializer, ProjectCommentSerializer

logger = logging.getLogger(__name__)


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Project.objects.select_related('user').prefetch_related(
            'files', 'dependencies', 'comments__user'
        )
        if self.request.user.is_authenticated:
            queryset = queryset.filter(Q(is_public=True) | Q(user=self.request.user))
        else:
            queryset = queryset.filter(is_public=True)
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Project.objects.filter(pk=instance.pk).update(views=F('views') + 1)
        instance.refresh_from_db()
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_file(self, request, pk=None):
        project = self.get_object()
        if project.user != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        name = request.data.get('name', '').strip()
        content = request.data.get('content', '')

        if not name:
            return Response({'error': 'File name is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Auto-detect file_type from extension
        file_type = 'py'
        if name.endswith('.c'):
            file_type = 'c'
        elif name.endswith(('.cpp', '.cc', '.cxx')):
            file_type = 'cpp'
        elif name.endswith('.py'):
            file_type = 'py'

        # Check for duplicate file names
        if ProjectFile.objects.filter(project=project, name=name).exists():
            return Response({'error': f'A file named "{name}" already exists'}, status=status.HTTP_400_BAD_REQUEST)

        file = ProjectFile.objects.create(
            project=project,
            name=name,
            content=content,
            file_type=file_type,
        )
        serializer = ProjectFileSerializer(file)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_dependency(self, request, pk=None):
        project = self.get_object()
        if project.user != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProjectDependencySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project=project)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_comment(self, request, pk=None):
        project = self.get_object()
        serializer = ProjectCommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project=project, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectFileViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        return ProjectFile.objects.filter(project_id=project_id)

    def perform_create(self, serializer):
        project_id = self.kwargs.get('project_id')
        try:
            project = Project.objects.get(id=project_id, user=self.request.user)
        except Project.DoesNotExist:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not own this project.")
        serializer.save(project=project)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.project.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not own this project.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.project.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not own this project.")
        instance.delete()
