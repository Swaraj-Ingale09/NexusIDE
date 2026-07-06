from django.contrib import admin
from apps.community.models import CommunityPost, PostComment, UserFollow


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'category', 'likes', 'views', 'created_at']
    search_fields = ['title', 'user__username']
    list_filter = ['category', 'created_at']


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'likes', 'created_at']
    search_fields = ['user__username', 'post__title']


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ['follower', 'following', 'created_at']
    search_fields = ['follower__username', 'following__username']
