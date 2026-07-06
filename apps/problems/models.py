from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class ProblemCategory(models.Model):
    """Problem categories for organization"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='code', help_text="FontAwesome icon class")
    
    class Meta:
        db_table = 'problem_categories'
        verbose_name_plural = "Problem Categories"
    
    def __str__(self):
        return self.name


class Problem(models.Model):
    """Competitive programming problems"""
    
    DIFFICULTY_CHOICES = [
        (1, 'Easy'),
        (2, 'Medium'),
        (3, 'Hard'),
        (4, 'Expert'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    # Basic Info
    title = models.CharField(max_length=300, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(help_text="Problem description with examples")
    explanation = models.TextField(blank=True, help_text="Detailed explanation of the problem")
    
    # Problem Details
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES, default=1)
    category = models.ForeignKey(ProblemCategory, on_delete=models.SET_NULL, null=True, related_name='problems')
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    
    # Constraints
    time_limit = models.FloatField(default=1.0, validators=[MinValueValidator(0.1)])  # seconds
    memory_limit = models.IntegerField(default=256, validators=[MinValueValidator(64)])  # MB
    
    # Metadata
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    views = models.IntegerField(default=0)
    submissions = models.IntegerField(default=0)
    accepted_submissions = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'problems'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['difficulty', 'category']),
            models.Index(fields=['-views']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_difficulty_display()})"
    
    def publish(self):
        """Publish the problem"""
        if self.status == 'draft':
            self.status = 'published'
            self.published_at = timezone.now()
            self.save()
    
    @property
    def acceptance_rate(self):
        """Calculate acceptance rate percentage"""
        if self.submissions == 0:
            return 0
        return round((self.accepted_submissions / self.submissions) * 100, 2)


class TestCase(models.Model):
    """Test cases for problems"""
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases')
    
    # Test data
    input_data = models.TextField(help_text="Input for the problem")
    expected_output = models.TextField(help_text="Expected output")
    
    # Metadata
    is_sample = models.BooleanField(default=False, help_text="Show in problem description")
    is_hidden = models.BooleanField(default=False, help_text="Used for final judging")
    explanation = models.TextField(blank=True, help_text="Explanation for sample test case")
    
    order = models.IntegerField(default=0, help_text="Display order")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'test_cases'
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['problem', 'is_sample']),
        ]
        unique_together = ['problem', 'order']
    
    def __str__(self):
        return f"{self.problem.title} - Test Case {self.order}"


class ProblemSubmission(models.Model):
    """Track submissions for problems"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('accepted', 'Accepted'),
        ('wrong_answer', 'Wrong Answer'),
        ('runtime_error', 'Runtime Error'),
        ('timeout', 'Time Limit Exceeded'),
        ('memory_limit', 'Memory Limit Exceeded'),
        ('compilation_error', 'Compilation Error'),
    ]
    
    # Submission Details
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='user_submissions')
    code = models.TextField()
    language = models.CharField(max_length=20, default='python')  # For future multi-language support
    
    # Execution Results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    passed_tests = models.IntegerField(default=0)
    total_tests = models.IntegerField(default=0)
    
    # Performance Metrics
    execution_time = models.FloatField(default=0, help_text="Execution time in seconds")
    memory_used = models.FloatField(default=0, help_text="Memory used in MB")
    
    # Error Tracking
    error_message = models.TextField(blank=True)
    failed_test_case = models.IntegerField(null=True, blank=True, help_text="Index of first failed test")
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    judged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'problem_submissions'
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['user', 'problem', '-submitted_at']),
            models.Index(fields=['problem', 'status']),
            models.Index(fields=['-submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.problem.title} ({self.status})"
    
    @property
    def is_accepted(self):
        return self.status == 'accepted'


class UserProblemStats(models.Model):
    """Track user progress on problems"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='problem_stats')
    
    # Statistics
    problems_solved = models.IntegerField(default=0)
    problems_attempted = models.IntegerField(default=0)
    total_submissions = models.IntegerField(default=0)
    total_accepted = models.IntegerField(default=0)
    
    # Difficulty breakdown
    easy_solved = models.IntegerField(default=0)
    medium_solved = models.IntegerField(default=0)
    hard_solved = models.IntegerField(default=0)
    expert_solved = models.IntegerField(default=0)
    
    # Performance
    best_acceptance_rate = models.FloatField(default=0)
    average_solve_time = models.FloatField(default=0, help_text="Average time in minutes")
    
    # Streaks
    longest_streak = models.IntegerField(default=0, help_text="Days")
    current_streak = models.IntegerField(default=0, help_text="Days")
    
    # Timestamps
    last_solved = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_problem_stats'
    
    def __str__(self):
        return f"{self.user.username} - {self.problems_solved} solved"


class ProblemAttempt(models.Model):
    """Track individual problem attempts for streak and progress"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_attempts')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='user_attempts')
    
    # Status
    is_solved = models.BooleanField(default=False)
    first_solved_at = models.DateTimeField(null=True, blank=True)
    
    # Attempt tracking
    attempts = models.IntegerField(default=0)
    best_execution_time = models.FloatField(null=True, blank=True)
    best_memory_used = models.FloatField(null=True, blank=True)
    
    # Timestamps
    first_attempt_at = models.DateTimeField(auto_now_add=True)
    last_attempt_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'problem_attempts'
        unique_together = ['user', 'problem']
        indexes = [
            models.Index(fields=['user', 'is_solved']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.problem.title} ({'✓' if self.is_solved else '✗'})"


class ProblemRating(models.Model):
    """User ratings and reviews for problems"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='problem_ratings')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='ratings')
    
    # Rating
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1-5 star rating"
    )
    difficulty_rating = models.IntegerField(
        default=0,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="User's perception of difficulty (optional)"
    )
    
    # Review
    review = models.TextField(blank=True)
    helpful_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'problem_ratings'
        unique_together = ['user', 'problem']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.problem.title} ({self.rating}★)"


class Contest(models.Model):
    """Time-limited coding contests"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('live', 'Live'),
        ('ended', 'Ended'),
    ]
    
    # Basic Info
    title = models.CharField(max_length=300)
    description = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_contests')
    
    # Timing
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.IntegerField(help_text="Duration in minutes")
    
    # Settings
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_public = models.BooleanField(default=True)
    max_participants = models.IntegerField(null=True, blank=True)
    
    # Problems
    problems = models.ManyToManyField(Problem, related_name='contests')
    
    # Statistics
    participants = models.IntegerField(default=0)
    submissions = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contests'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['status', 'start_time']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_live(self):
        now = timezone.now()
        return self.start_time <= now <= self.end_time
    
    @property
    def has_started(self):
        return timezone.now() >= self.start_time
    
    @property
    def has_ended(self):
        return timezone.now() >= self.end_time


class ContestParticipation(models.Model):
    """Track user participation in contests"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contest_participations')
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, related_name='participations')
    
    # Performance
    problems_solved = models.IntegerField(default=0)
    total_score = models.IntegerField(default=0)
    rank = models.IntegerField(null=True, blank=True)
    penalty_time = models.IntegerField(default=0, help_text="Penalty in minutes")
    
    # Timestamps
    registered_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'contest_participations'
        unique_together = ['user', 'contest']
        ordering = ['rank', 'total_score']
    
    def __str__(self):
        return f"{self.user.username} - {self.contest.title} (Rank: {self.rank})"
