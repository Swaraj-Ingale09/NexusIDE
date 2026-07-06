from rest_framework import serializers
from django.contrib.auth.models import User
from apps.users.models import UserProfile, Achievement, UserSession, UserActivity, UserSatisfaction


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'avatar', 'bio', 'xp_points', 'level', 'streak_days', 'problems_solved', 'last_activity']


class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ['id', 'title', 'description', 'icon', 'earned_at']


class UserSessionSerializer(serializers.ModelSerializer):
    session_duration = serializers.SerializerMethodField()
    session_duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSession
        fields = ['id', 'user', 'login_time', 'logout_time', 'ip_address', 'session_duration', 'session_duration_formatted']
    
    def get_session_duration(self, obj):
        return obj.get_session_duration()
    
    def get_session_duration_formatted(self, obj):
        return obj.get_session_duration_formatted()


class UserActivitySerializer(serializers.ModelSerializer):
    activity_type_display = serializers.SerializerMethodField()
    
    class Meta:
        model = UserActivity
        fields = ['id', 'user', 'activity_type', 'activity_type_display', 'description', 'timestamp']
    
    def get_activity_type_display(self, obj):
        return obj.get_activity_type_display()


class UserSatisfactionSerializer(serializers.ModelSerializer):
    rating_display = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSatisfaction
        fields = ['id', 'user', 'rating', 'rating_display', 'review', 'features_liked', 'features_to_improve', 'would_recommend', 'submitted_at']
    
    def get_rating_display(self, obj):
        return f"{obj.rating}★"


class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, write_only=True, required=True)
    password2 = serializers.CharField(min_length=8, write_only=True, required=False)

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2') or password

        if password != password2:
            raise serializers.ValidationError({"password": "Passwords must match."})
        
        # Run Django's password validators
        from django.contrib.auth.password_validation import validate_password
        try:
            validate_password(password)
        except Exception as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists."})
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ComprehensiveUserAnalyticsSerializer(serializers.Serializer):
    """Comprehensive analytics for a single user"""
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    profile_stats = serializers.DictField()
    activity_summary = serializers.DictField()
    ai_usage_stats = serializers.DictField()
    code_stats = serializers.DictField()
    session_stats = serializers.DictField()
    recent_activities = UserActivitySerializer(many=True)
    recent_executions = serializers.ListField()
    ai_queries_summary = serializers.DictField()


class SiteWideAnalyticsSerializer(serializers.Serializer):
    """Site-wide analytics and metrics"""
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    total_sessions = serializers.IntegerField()
    total_code_executions = serializers.IntegerField()
    total_ai_queries = serializers.IntegerField()
    total_ai_tokens_used = serializers.IntegerField()
    total_snippets = serializers.IntegerField()
    average_session_duration = serializers.FloatField()
    user_engagement = serializers.DictField()
    activity_breakdown = serializers.DictField()
    ai_usage_breakdown = serializers.DictField()
    language_popularity = serializers.DictField()
    peak_usage_time = serializers.CharField()
