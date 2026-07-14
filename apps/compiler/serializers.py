from rest_framework import serializers
from apps.compiler.models import CodeSnippet, ExecutionHistory, CodeLike, TerminalExecution, TerminalExecutionStep, TerminalInput


class CodeSnippetSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    
    class Meta:
        model = CodeSnippet
        fields = ['id', 'user', 'title', 'description', 'code', 'language', 'is_public',
                  'likes', 'views', 'fork_count', 'tags', 'likes_count', 'is_liked', 
                  'created_at', 'updated_at', 'parent_snippet']
        read_only_fields = ['user', 'created_at', 'updated_at', 'likes', 'views', 'fork_count']

    def get_likes_count(self, obj):
        return getattr(obj, 'likes_count', obj.user_likes.count())

    def get_is_liked(self, obj):
        if hasattr(obj, 'is_liked'):
            return bool(obj.is_liked)

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CodeLike.objects.filter(user=request.user, code_snippet=obj).exists()
        return False


class ExecutionHistorySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = ExecutionHistory
        fields = ['id', 'user', 'code', 'output', 'error', 'status', 
                  'execution_time', 'memory_used', 'stdin', 'created_at']
        read_only_fields = ['user', 'created_at', 'execution_time', 'memory_used', 'status']


class CodeExecutionSerializer(serializers.Serializer):
    code = serializers.CharField()
    stdin = serializers.CharField(required=False, allow_blank=True)
    language = serializers.ChoiceField(choices=['python', 'c', 'cpp', 'sql'], required=False, default='python')
    snippet_id = serializers.IntegerField(required=False)


class AIAssistantSerializer(serializers.Serializer):
    code = serializers.CharField()
    action = serializers.ChoiceField(choices=['explain', 'fix', 'optimize', 'debug', 'chat', 'format', 'test', 'generate'])
    language = serializers.ChoiceField(choices=['python', 'c', 'cpp', 'sql'], required=False, default='python')
    error = serializers.CharField(required=False, allow_blank=True)
    context = serializers.CharField(required=False, allow_blank=True)
    output = serializers.CharField(required=False, allow_blank=True)


# ═══════════════════════════════════════════════════════════════
# Terminal Execution Serializers
# ═══════════════════════════════════════════════════════════════

class TerminalExecutionStepSerializer(serializers.ModelSerializer):
    """Serializer for individual execution steps."""
    
    class Meta:
        model = TerminalExecutionStep
        fields = ['id', 'step_type', 'content', 'line_number', 'execution_time_at_step', 'metadata', 'created_at']
        read_only_fields = ['created_at']


class TerminalInputSerializer(serializers.ModelSerializer):
    """Serializer for user inputs during interactive execution."""
    
    class Meta:
        model = TerminalInput
        fields = ['id', 'input_number', 'content', 'provided_at', 'execution_time_at_input', 'prompt_text']
        read_only_fields = ['provided_at']


class TerminalExecutionSerializer(serializers.ModelSerializer):
    """Serializer for terminal execution sessions with steps."""
    
    user = serializers.StringRelatedField(read_only=True)
    steps = TerminalExecutionStepSerializer(many=True, read_only=True)
    inputs = TerminalInputSerializer(many=True, read_only=True)
    
    class Meta:
        model = TerminalExecution
        fields = ['id', 'user', 'code', 'language', 'status', 'started_at', 'completed_at',
                  'execution_time', 'total_lines', 'error_lines', 'return_code', 'metadata',
                  'steps', 'inputs']
        read_only_fields = ['user', 'started_at', 'completed_at', 'execution_time', 
                          'total_lines', 'error_lines', 'return_code', 'steps', 'inputs']


class TerminalExecutionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing terminal executions (without steps)."""
    
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = TerminalExecution
        fields = ['id', 'user', 'language', 'status', 'started_at', 'completed_at',
                  'execution_time', 'total_lines', 'error_lines', 'return_code']
        read_only_fields = ['user', 'started_at', 'completed_at', 'execution_time', 
                          'total_lines', 'error_lines', 'return_code']


class TerminalExecutionCreateSerializer(serializers.Serializer):
    """Serializer for creating a new terminal execution."""
    
    code = serializers.CharField()
    language = serializers.ChoiceField(choices=['python', 'c', 'cpp', 'sql'], default='python')
    snippet_id = serializers.IntegerField(required=False, allow_null=True)
    input_lines = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of inputs for interactive programs"
    )
