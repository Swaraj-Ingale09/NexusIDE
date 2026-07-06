from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    xp_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    streak_days = models.IntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)
    problems_solved = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Enhanced tracking
    total_ai_tokens_used = models.IntegerField(default=0)  # Total AI tokens consumed
    total_code_executions = models.IntegerField(default=0)  # Total code runs
    total_snippets_created = models.IntegerField(default=0)  # Total snippets
    total_session_time = models.IntegerField(default=0)  # Total session time in seconds
    last_login = models.DateTimeField(null=True, blank=True)
    login_count = models.IntegerField(default=0)  # Total logins
    code_quality_score = models.FloatField(default=0.0)  # AI-based code quality score
    favorite_language = models.CharField(max_length=20, blank=True, default='python')
    
    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    class Meta:
        db_table = 'user_profiles'


class Achievement(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='star')
    earned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username} - {self.title}"

    class Meta:
        db_table = 'achievements'


class UserSession(models.Model):
    """Track user login sessions for admin dashboard"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    def get_session_duration(self):
        """Get session duration in seconds"""
        if self.logout_time:
            return (self.logout_time - self.login_time).total_seconds()
        return (timezone.now() - self.login_time).total_seconds()
    
    def get_session_duration_formatted(self):
        """Get formatted session duration"""
        seconds = self.get_session_duration()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m"
        elif minutes > 0:
            return f"{int(minutes)}m {int(secs)}s"
        else:
            return f"{int(secs)}s"

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"

    class Meta:
        db_table = 'user_sessions'
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', '-login_time']),
        ]


class UserActivity(models.Model):
    """Track what users are doing in the app"""
    ACTIVITY_CHOICES = [
        ('compile', 'Code Compilation'),
        ('snippet_create', 'Snippet Created'),
        ('snippet_view', 'Snippet Viewed'),
        ('project_create', 'Project Created'),
        ('project_edit', 'Project Edited'),
        ('community_post', 'Community Post'),
        ('community_like', 'Community Like'),
        ('community_comment', 'Community Comment'),
        ('ai_chat', 'AI Chat Usage'),
        ('format_code', 'Code Format'),
        ('analyze_code', 'Code Analysis'),
        ('email_verified', 'Email Verified'),
        ('password_reset', 'Password Reset'),
        ('page_view', 'Page View'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_CHOICES)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()}"

    class Meta:
        db_table = 'user_activities'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type', '-timestamp']),
        ]


class UserHeartbeat(models.Model):
    """Track active user presence - sent every minute when user is active"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='heartbeats')
    timestamp = models.DateTimeField(auto_now_add=True)
    page = models.CharField(max_length=255, blank=True)  # Current page user is on
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.timestamp}"
    
    class Meta:
        db_table = 'user_heartbeats'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
        ]


class UserSatisfaction(models.Model):
    """Track user satisfaction and reviews"""
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='satisfaction_ratings')
    rating = models.IntegerField(choices=RATING_CHOICES, default=5)
    review = models.TextField(blank=True)
    features_liked = models.TextField(help_text="Comma-separated list of liked features", blank=True)
    features_to_improve = models.TextField(help_text="Comma-separated list of features to improve", blank=True)
    would_recommend = models.BooleanField(default=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.rating}★"

    class Meta:
        db_table = 'user_satisfaction'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['user', '-submitted_at']),
            models.Index(fields=['rating']),
        ]


class AdminLog(models.Model):
    """Track admin dashboard access"""
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='admin_logs')
    action = models.CharField(max_length=200)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.admin_user.username} - {self.action} at {self.timestamp}"

    class Meta:
        db_table = 'admin_logs'
        ordering = ['-timestamp']


class EmailVerificationToken(models.Model):
    """Store email verification tokens for new user registrations"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verification_tokens')
    email = models.EmailField()
    token = models.CharField(max_length=6, unique=True)  # 6-digit code
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    attempts = models.IntegerField(default=0)
    
    def is_valid(self):
        """Check if token is still valid"""
        if self.is_verified:
            return False
        if timezone.now() > self.expires_at:
            return False
        if self.attempts >= 5:  # Max 5 attempts
            return False
        return True
    
    def mark_verified(self):
        """Mark email as verified"""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()
    
    def increment_attempts(self):
        """Increment attempt counter"""
        self.attempts += 1
        self.save()
    
    @staticmethod
    def generate_token():
        """Generate a cryptographically secure 6-digit code"""
        return ''.join(secrets.choice('0123456789') for _ in range(6))
    
    def __str__(self):
        return f"{self.user.username} - Email Verification"
    
    class Meta:
        db_table = 'email_verification_tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['token']),
        ]


class PasswordResetToken(models.Model):
    """Store password reset tokens with expiry"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    email = models.EmailField()
    token = models.CharField(max_length=6, unique=True)  # 6-digit code
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.IntegerField(default=0)
    
    def is_valid(self):
        """Check if token is still valid"""
        if self.is_used:
            return False
        if timezone.now() > self.expires_at:
            return False
        if self.attempts >= 5:  # Max 5 attempts
            return False
        return True
    
    def mark_used(self):
        """Mark token as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()
    
    def increment_attempts(self):
        """Increment attempt counter"""
        self.attempts += 1
        self.save()
    
    @staticmethod
    def generate_token():
        """Generate a cryptographically secure 6-digit code"""
        return ''.join(secrets.choice('0123456789') for _ in range(6))
    
    def __str__(self):
        return f"{self.user.username} - Password Reset Token"
    
    class Meta:
        db_table = 'password_reset_tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['token']),
        ]
