from rest_framework import serializers
from apps.community.models import CommunityPost, PostComment, UserFollow


class PostCommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = PostComment
        fields = ['id', 'user', 'content', 'likes', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


class CommunityPostSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    comments = PostCommentSerializer(read_only=True, many=True)

    class Meta:
        model = CommunityPost
        fields = ['id', 'user', 'title', 'content', 'category', 'likes', 'views', 'comments', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at', 'likes', 'views']


class UserFollowSerializer(serializers.ModelSerializer):
    follower = serializers.StringRelatedField(read_only=True)
    following = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = UserFollow
        fields = ['id', 'follower', 'following', 'created_at']
        read_only_fields = ['created_at']
