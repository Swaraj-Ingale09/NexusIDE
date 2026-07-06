from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class CodeSnippet(models.Model):
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('c', 'C'),
        ('cpp', 'C++'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='code_snippets')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    code = models.TextField()
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='python')
    is_public = models.BooleanField(default=False)
    likes = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    fork_count = models.IntegerField(default=0)
    parent_snippet = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='forks')
    tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'code_snippets'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_public', '-likes']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class ExecutionHistory(models.Model):
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
        ('running', 'Running'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='execution_history')
    code_snippet = models.ForeignKey(CodeSnippet, null=True, blank=True, on_delete=models.SET_NULL, related_name='executions')
    code = models.TextField()
    output = models.TextField(blank=True)
    error = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    execution_time = models.FloatField(default=0)
    memory_used = models.FloatField(default=0)
    stdin = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'execution_history'
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.status} ({self.created_at})"


class CodeLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code_snippet = models.ForeignKey(CodeSnippet, on_delete=models.CASCADE, related_name='user_likes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'code_snippet']
        db_table = 'code_likes'

    def __str__(self):
        return f"{self.user.username} likes {self.code_snippet.title}"


class AIQuery(models.Model):
    """Store all AI queries and responses for caching and analytics"""
    
    ACTION_CHOICES = [
        ('fix', 'Fix Code'),
        ('explain', 'Explain Code'),
        ('optimize', 'Optimize Code'),
        ('review', 'Review Code'),
        ('suggest', 'Suggest Improvements'),
        ('generate', 'Generate Code'),
        ('chat', 'Chat'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_queries', null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Query input
    query_input = models.TextField()  # The code or prompt sent to AI
    query_hash = models.CharField(max_length=64, db_index=True)  # Hash for quick lookup
    
    # Response output
    response_output = models.TextField()  # The AI response/generated code
    
    # Metadata
    provider = models.CharField(max_length=50, default='openrouter')  # Which AI provider (openrouter, nvidia, fallback)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    execution_time = models.FloatField(default=0)  # Time taken in seconds
    
    # Additional fields
    model_name = models.CharField(max_length=100, blank=True)  # Model used
    tokens_used = models.IntegerField(default=0)  # Tokens consumed
    error_message = models.TextField(blank=True)  # If failed, why
    
    # Timestamps and tracking
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    reuse_count = models.IntegerField(default=0)  # How many times this cached response was used
    
    # Related code snippet (optional)
    code_snippet = models.ForeignKey(CodeSnippet, null=True, blank=True, on_delete=models.SET_NULL, related_name='ai_queries')
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'ai_queries'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['query_hash']),  # For fast cache lookup
            models.Index(fields=['action', 'status']),
            models.Index(fields=['provider']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"{user_str} - {self.action} ({self.status})"
    
    def increment_reuse(self):
        """Increment the reuse count when cache is hit"""
        self.reuse_count += 1
        self.save(update_fields=['reuse_count'])


class AIQueryCache(models.Model):
    """Fast lookup cache for similar queries (deduplication)"""
    
    query_hash = models.CharField(max_length=64, unique=True, db_index=True)
    action = models.CharField(max_length=20)
    
    # The cached response
    cached_response = models.TextField()
    cached_provider = models.CharField(max_length=50)
    
    # Cache statistics
    hit_count = models.IntegerField(default=1)  # How many times used
    last_hit = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Cache expiration
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_hit']
        db_table = 'ai_query_cache'
        indexes = [
            models.Index(fields=['query_hash']),
            models.Index(fields=['action']),
            models.Index(fields=['last_hit']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.hit_count} hits"
    
    def is_expired(self):
        """Check if cache entry has expired"""
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def increment_hits(self):
        """Increment hit count"""
        self.hit_count += 1
        self.save(update_fields=['hit_count', 'last_hit'])


class TerminalExecution(models.Model):
    """
    Terminal-style code execution session.
    Stores the overall execution with metadata, replacing ExecutionHistory for terminal mode.
    """
    
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
        ('stopped', 'Stopped'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='terminal_executions')
    code_snippet = models.ForeignKey(CodeSnippet, null=True, blank=True, on_delete=models.SET_NULL, related_name='terminal_executions')
    
    # Code and language
    code = models.TextField()
    language = models.CharField(max_length=20, choices=[('python', 'Python'), ('c', 'C'), ('cpp', 'C++')], default='python')
    
    # Execution status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    execution_time = models.FloatField(default=0, help_text="Total execution time in seconds")
    
    # Terminal stats
    total_lines = models.IntegerField(default=0, help_text="Total output lines")
    error_lines = models.IntegerField(default=0, help_text="Number of error lines")
    return_code = models.IntegerField(default=0)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional execution metadata")
    
    class Meta:
        ordering = ['-started_at']
        db_table = 'terminal_executions'
        indexes = [
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - Terminal Execution ({self.status})"
    
    def is_running(self):
        """Check if execution is still running."""
        return self.status == 'running'
    
    def mark_completed(self):
        """Mark execution as completed."""
        from django.utils import timezone
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.execution_time = (self.completed_at - self.started_at).total_seconds()
        self.save()


class TerminalExecutionStep(models.Model):
    """
    Individual execution step/line in terminal output.
    Similar to VS Code terminal where each line is tracked separately.
    """
    
    STEP_TYPE_CHOICES = [
        ('output', 'Standard Output'),
        ('error', 'Error Output'),
        ('input', 'User Input'),
        ('step', 'Execution Step Marker'),
        ('status', 'Status Update'),
        ('summary', 'Execution Summary'),
    ]
    
    execution = models.ForeignKey(TerminalExecution, on_delete=models.CASCADE, related_name='steps')
    
    # Step content
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES, default='output')
    content = models.TextField(help_text="The actual output/error text")
    line_number = models.IntegerField(help_text="Line number in terminal output")
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    execution_time_at_step = models.FloatField(default=0, help_text="Total execution time when this step was generated")
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text="Step-specific metadata (error_type, status, etc)")
    
    class Meta:
        ordering = ['line_number']
        db_table = 'terminal_execution_steps'
        indexes = [
            models.Index(fields=['execution', 'line_number']),
            models.Index(fields=['step_type']),
        ]
    
    def __str__(self):
        return f"Step {self.line_number} - {self.step_type}"


class TerminalInput(models.Model):
    """
    Stores user inputs provided during interactive terminal execution.
    Multiple inputs can be provided for programs with multiple input() calls.
    """
    
    execution = models.ForeignKey(TerminalExecution, on_delete=models.CASCADE, related_name='inputs')
    
    # Input details
    input_number = models.IntegerField(help_text="Order of input (1st, 2nd, 3rd input, etc)")
    content = models.TextField(help_text="The user-provided input")
    
    # Timing
    provided_at = models.DateTimeField(auto_now_add=True)
    execution_time_at_input = models.FloatField(help_text="Total execution time when input was provided")
    
    # Metadata
    prompt_text = models.TextField(blank=True, help_text="The prompt text the program showed before requesting input")
    
    class Meta:
        ordering = ['input_number']
        db_table = 'terminal_inputs'
        unique_together = ['execution', 'input_number']
    
    def __str__(self):
        return f"Input {self.input_number} for Execution {self.execution.id}"
