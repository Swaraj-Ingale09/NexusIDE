from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.db.models import F
from apps.community.models import CommunityPost, PostComment, UserFollow, PostLike
from apps.community.serializers import CommunityPostSerializer, PostCommentSerializer, UserFollowSerializer


class CommunityFeedViewSet(viewsets.ModelViewSet):
    serializer_class = CommunityPostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['category', 'user']
    search_fields = ['title', 'content']
    ordering = ['-created_at']

    def get_queryset(self):
        return CommunityPost.objects.select_related('user').prefetch_related('comments__user').all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        # Atomic increment to avoid race conditions
        CommunityPost.objects.filter(pk=kwargs['pk']).update(views=F('views') + 1)
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        post = CommunityPost.objects.get(pk=pk)
        like_obj, created = PostLike.objects.get_or_create(user=request.user, post=post)
        if not created:
            like_obj.delete()
            CommunityPost.objects.filter(pk=pk).update(likes=F('likes') - 1)
            return Response({'liked': False, 'likes': post.likes - 1})
        CommunityPost.objects.filter(pk=pk).update(likes=F('likes') + 1)
        return Response({'liked': True, 'likes': post.likes + 1})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_comment(self, request, pk=None):
        post = self.get_object()
        serializer = PostCommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(post=post, user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def feed(self, request):
        user_follows = UserFollow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        posts = CommunityPost.objects.filter(user_id__in=user_follows) | CommunityPost.objects.filter(user=request.user)
        posts = posts.select_related('user').prefetch_related('comments__user').distinct()
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
