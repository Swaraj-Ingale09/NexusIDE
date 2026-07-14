from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from django.db.models import Q, F, Count, Exists, OuterRef, Value, BooleanField
from django.conf import settings
import logging
from apps.compiler.models import CodeSnippet, ExecutionHistory, CodeLike, TerminalExecution, TerminalExecutionStep, TerminalInput
from apps.compiler.serializers import (
    CodeSnippetSerializer, ExecutionHistorySerializer, CodeExecutionSerializer, AIAssistantSerializer,
    TerminalExecutionSerializer, TerminalExecutionListSerializer, TerminalExecutionCreateSerializer
)
from apps.compiler.executor import execute_python_code, execute_code
from apps.compiler.docker_executor import get_executor as get_docker_executor
from apps.compiler.terminal_executor import TerminalExecutor
from django.conf import settings as app_settings
from apps.compiler.ai_helper import get_ai_explanation, get_ai_fix, get_ai_suggestions, get_ai_format, get_ai_test_generation
from apps.compiler.code_analyzer import CodeAnalyzer
from apps.compiler.formatter import PythonFormatter
from apps.compiler.python_parser import PythonParser, analyze_python_code
import re

logger = logging.getLogger(__name__)


def _extract_code_from_ai_response(text, language='python'):
    """Extract code block from an AI response text.
    
    Handles responses like:
        Here's the fixed code:
        ```python
        code here
        ```
        Some explanation...
    
    Also handles responses that are just raw code (no markdown blocks).
    """
    if not text:
        return None
    
    # Try to find markdown code blocks first
    # Match ```lang\ncode\n``` or ```\ncode\n```
    pattern = r'```(?:' + re.escape(language) + r'|c|cpp|c\+\+|python|javascript|java)?\s*\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if matches:
        # Return the longest code block (most likely the main code)
        best = max(matches, key=len).strip()
        if len(best) > 10:  # Minimum viable code
            return best
    
    # If no code blocks, check if the entire response looks like code
    # Heuristic: starts with common code patterns
    stripped = text.strip()
    code_starters = [
        '#include', 'int main', 'void ', 'def ', 'class ', 'import ',
        'from ', 'public ', 'private ', 'static ', 'const ', 'struct ',
        '#define', '#pragma', '#ifndef',
    ]
    
    for starter in code_starters:
        if stripped.startswith(starter):
            # Find where code ends and explanation begins
            lines = stripped.split('\n')
            code_lines = []
            for line in lines:
                # Stop if we hit a line that looks like natural language explanation
                if (len(line.strip()) > 0 
                    and not line.strip().startswith(('//', '#', '/*', '*', '///'))
                    and not any(line.strip().startswith(s) for s in code_starters)
                    and line.strip()[0:1].isupper() 
                    and not any(c in line for c in ['{', '}', '(', ')', ';', ':', '=', '>', '<', '+', '-', '*', '/'])
                    and len(line.split()) > 6):  # Long wordy line = explanation
                    break
                code_lines.append(line)
            
            extracted = '\n'.join(code_lines).strip()
            if len(extracted) > 10:
                return extracted
    
    return None


class CodeSnippetViewSet(viewsets.ModelViewSet):
    serializer_class = CodeSnippetSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['language', 'is_public', 'user']
    search_fields = ['title', 'description', 'tags']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = CodeSnippet.objects.select_related('user', 'parent_snippet').annotate(
            likes_count=Count('user_likes', distinct=True)
        )
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                is_liked=Exists(
                    CodeLike.objects.filter(
                        user=self.request.user,
                        code_snippet=OuterRef('pk')
                    )
                )
            )
        else:
            queryset = queryset.annotate(
                is_liked=Value(False, output_field=BooleanField())
            )

        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        # Atomic increment to avoid race conditions
        from apps.compiler.models import CodeSnippet as CS
        CS.objects.filter(pk=kwargs['pk']).update(views=F('views') + 1)
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def like(self, request, pk=None):
        snippet = self.get_object()
        like, created = CodeLike.objects.get_or_create(user=request.user, code_snippet=snippet)
        if not created:
            like.delete()
            CodeSnippet.objects.filter(pk=pk).update(likes=F('likes') - 1)
            return Response({'liked': False})
        CodeSnippet.objects.filter(pk=pk).update(likes=F('likes') + 1)
        return Response({'liked': True})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def fork(self, request, pk=None):
        parent = self.get_object()
        new_snippet = CodeSnippet.objects.create(
            user=request.user,
            title=f"Fork of {parent.title}",
            description=parent.description,
            code=parent.code,
            language=parent.language,
            is_public=False,
            parent_snippet=parent,
            tags=parent.tags
        )
        parent.fork_count += 1
        parent.save()
        return Response(CodeSnippetSerializer(new_snippet).data, status=status.HTTP_201_CREATED)


class ExecutionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExecutionHistorySerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-created_at']

    def get_queryset(self):
        return ExecutionHistory.objects.select_related('user', 'code_snippet').filter(user=self.request.user)


class ExecuteCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CodeExecutionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']
        stdin = serializer.validated_data.get('stdin', '')
        language = serializer.validated_data.get('language', 'python')

        # Enforce code size limit
        max_code_size = getattr(settings, 'MAX_CODE_SIZE', 1000000)
        if len(code) > max_code_size:
            return Response({
                'output': '',
                'error': f'Code exceeds maximum size of {max_code_size} characters',
                'status': 'error',
                'execution_time': 0,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Ensure proper UTF-8 encoding
        try:
            if isinstance(code, bytes):
                code = code.decode('utf-8', errors='replace')
            if isinstance(stdin, bytes):
                stdin = stdin.decode('utf-8', errors='replace')
        except Exception:
            return Response({
                'output': '',
                'error': 'Encoding error: Unable to decode input',
                'status': 'error',
                'execution_time': 0,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Execute code using Docker sandbox when enabled, fallback to subprocess
        try:
            if getattr(app_settings, 'DOCKER_ENABLED', False):
                try:
                    docker_exec = get_docker_executor(language)
                    result = docker_exec.execute(code, stdin=stdin)
                except Exception as e:
                    logger.warning("Docker executor failed, falling back to subprocess: %s", e)
                    result = execute_code(code, language=language, stdin=stdin)
            else:
                result = execute_code(code, language=language, stdin=stdin)
        except Exception as e:
            logger.exception("Code execution failed")
            result = {
                'output': '',
                'error': f'Execution system error: {str(e)}',
                'status': 'error',
                'execution_time': 0,
                'return_code': -1,
                'artifacts': [],
            }

        # Ensure output is properly encoded
        try:
            result['output'] = result.get('output', '') or ''
            result['error'] = result.get('error', '') or ''
            result['output'] = result['output'].encode('utf-8', errors='replace').decode('utf-8')
            result['error'] = result['error'].encode('utf-8', errors='replace').decode('utf-8')
        except Exception:
            pass

        # Always try to save history, but NEVER let it block the response
        execution = None
        try:
            # Store artifact metadata only (not the base64 data) to avoid DB bloat
            raw_artifacts = result.get('artifacts', [])
            artifact_meta = [
                {'type': a.get('type', 'unknown'), 'name': a.get('name', ''), 'ext': a.get('ext', '')}
                for a in raw_artifacts
            ]
            execution = ExecutionHistory.objects.create(
                user=request.user,
                code=code,
                output=result.get('output', ''),
                error=result.get('error', ''),
                status=result.get('status', 'error'),
                execution_time=result.get('execution_time', 0),
                stdin=stdin,
                metadata={"artifacts": artifact_meta, "language": language},
            )

            if 'snippet_id' in serializer.validated_data:
                try:
                    snippet = CodeSnippet.objects.get(id=serializer.validated_data['snippet_id'])
                    execution.code_snippet = snippet
                    execution.save()
                except (CodeSnippet.DoesNotExist, Exception):
                    pass
        except Exception as e:
            logger.warning("Failed to save execution history: %s", e)

        # ALWAYS return a response with the execution result
        response_data = {
            'id': execution.id if execution else None,
            'code': code,
            'output': result.get('output', ''),
            'error': result.get('error', ''),
            'status': result.get('status', 'error'),
            'execution_time': result.get('execution_time', 0),
            'stdin': stdin,
            'artifacts': result.get('artifacts', []),
            'created_at': execution.created_at.isoformat() if execution else None,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class AIAssistantView(APIView):
    """
    AI Assistant endpoint — explain, fix, optimize, debug, format, test, chat.
    Reads code, output, and errors from the editor for context-aware responses.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.compiler.ai_providers import get_multi_provider_ai, FallbackResponses
        from config.rate_limiter import AI_FEATURE_LIMITS, AI_DEFAULT_LIMITER, get_client_identifier

        serializer = AIAssistantSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']
        action = serializer.validated_data['action']
        language = serializer.validated_data.get('language', 'python')
        error = serializer.validated_data.get('error', '')
        context = serializer.validated_data.get('context', '')
        output = serializer.validated_data.get('output', '')

        # Per-feature rate limit: 3 uses per feature per hour
        identifier = get_client_identifier(request)
        limiter = AI_FEATURE_LIMITS.get(action, AI_DEFAULT_LIMITER)
        if not limiter.is_allowed(identifier):
            remaining = limiter.get_remaining(identifier)
            seconds = limiter.get_seconds_until_reset(identifier)
            minutes = max(1, seconds // 60)
            return Response({
                'error': f'Daily limit reached for "{action}". Refreshes in {minutes} minutes.',
                'remaining': remaining,
                'refresh_seconds': seconds,
                'feature': action,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # Build context string from output/error so AI understands the full picture
        extra_context = ''
        if error:
            extra_context += f"\n\nExecution Error:\n{error}"
        if output:
            extra_context += f"\n\nProgram Output:\n{output}"
        if context:
            extra_context += f"\n\nUser says: {context}"

        try:
            ai = get_multi_provider_ai()
            result = None
            response_text = None

            if action == 'explain':
                result = ai.explain_inline(code, language=language)
                response_text = result.get('explanation', '')
            elif action == 'fix':
                result = ai.auto_fix(code, error if error else None, language=language)
                response_text = result.get('fixed_code', '')
            elif action == 'optimize':
                result = ai.optimize_inline(code, language=language)
                response_text = result.get('suggestion', '')
            elif action == 'debug':
                # Debug uses fix provider but with full error + output context
                debug_error = error or (output if 'Error' in output else '')
                result = ai.auto_fix(code, debug_error if debug_error else None, language=language)
                response_text = result.get('fixed_code', '')
            elif action == 'format':
                from apps.compiler.ai_helper import get_ai_format
                response_text = get_ai_format(code)
                result = {'success': True, 'provider': 'local'}
            elif action == 'test':
                from apps.compiler.ai_helper import get_ai_test_generation
                response_text = get_ai_test_generation(code) or "Could not generate tests"
                result = {'success': True, 'provider': 'local'}
            elif action == 'chat':
                # Chat sends full context to AI
                chat_result = ai._call_provider('explain', code + extra_context)
                if chat_result:
                    response_text = chat_result
                    result = {'success': True, 'provider': ai._get_last_provider_used()}
                else:
                    result = {'success': False}
            elif action == 'generate':
                # Generate code from natural language prompt
                gen_result = ai.generate_code(context or code, language=language)
                if gen_result and gen_result.get('success'):
                    response_text = gen_result.get('generated_code', '')
                    result = gen_result
                else:
                    result = {'success': False}
            else:
                response_text = f"Unknown action: {action}. Available: explain, fix, optimize, debug, format, test, chat, generate"
                result = {'success': False, 'provider': 'unknown'}

            # If provider failed, use fallback
            if not response_text or (result and not result.get('success', False)):
                fallback_map = {
                    'explain': FallbackResponses.explain_fallback(code),
                    'fix': FallbackResponses.fix_fallback(code, error),
                    'optimize': FallbackResponses.optimize_fallback(code),
                    'debug': FallbackResponses.fix_fallback(code, error or output),
                    'chat': FallbackResponses.explain_fallback(code),
                    'generate': '',
                }
                response_text = fallback_map.get(action, 'AI service unavailable')
                provider = 'fallback'
            else:
                provider = result.get('provider', 'unknown') if result else 'local'

            extracted = _extract_code_from_ai_response(response_text, language)

            # For generate action, if extraction failed, use the raw response as code
            if action == 'generate' and not extracted and response_text:
                extracted = response_text.strip()

            return Response({
                'response': response_text,
                'provider': provider,
                'extracted_code': extracted,
                'action': action,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("AI action '%s' failed: %s", action, str(e))
            # Return a useful fallback instead of an error
            fallback_map = {
                'explain': FallbackResponses.explain_fallback(code),
                'fix': FallbackResponses.fix_fallback(code, error),
                'optimize': FallbackResponses.optimize_fallback(code),
                'format': code,
                'test': '# Could not generate tests',
                'chat': FallbackResponses.explain_fallback(code),
                'generate': '# Could not generate code. Please try again.',
            }
            fallback_text = fallback_map.get(action, 'AI service unavailable. Please try again.')
            return Response({
                'response': fallback_text,
                'provider': 'fallback',
                'extracted_code': _extract_code_from_ai_response(fallback_text, language),
                'action': action,
            }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════════
# Terminal Execution Views - VS Code-style streaming output
# ═══════════════════════════════════════════════════════════════

class TerminalExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing terminal executions.
    Provides endpoints to view execution history and details.
    """
    
    serializer_class = TerminalExecutionSerializer
    permission_classes = [IsAuthenticated]
    ordering = ['-started_at']
    
    def get_queryset(self):
        """Only return executions for the current user."""
        return TerminalExecution.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Use lightweight serializer for list view."""
        if self.action == 'list':
            return TerminalExecutionListSerializer
        return TerminalExecutionSerializer
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get currently running executions."""
        active_executions = self.get_queryset().filter(status='running')
        serializer = TerminalExecutionListSerializer(active_executions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def stop(self, request, pk=None):
        """Stop a running execution."""
        execution = self.get_object()
        if execution.status == 'running':
            execution.status = 'stopped'
            execution.save()
            return Response({'status': 'stopped'})
        return Response({'error': 'Execution is not running'}, status=status.HTTP_400_BAD_REQUEST)


class TerminalExecuteView(APIView):
    """
    API endpoint for executing code in terminal mode with streaming output.
    Supports both simple execution and interactive input.
    
    Usage:
        POST /api/compiler/terminal/execute/
        {
            "code": "print('hello')",
            "language": "python",
            "input_lines": ["input1", "input2"]  # Optional for interactive programs
        }
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Execute code in terminal mode with streaming output."""
        serializer = TerminalExecutionCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        language = serializer.validated_data.get('language', 'python')
        snippet_id = serializer.validated_data.get('snippet_id')
        input_lines = serializer.validated_data.get('input_lines', [])
        
        try:
            # Create terminal execution record
            execution = TerminalExecution.objects.create(
                user=request.user,
                code=code,
                language=language,
                status='running'
            )
            
            if snippet_id:
                try:
                    snippet = CodeSnippet.objects.get(id=snippet_id)
                    execution.code_snippet = snippet
                    execution.save()
                except CodeSnippet.DoesNotExist:
                    pass
            
            # Execute code and stream output
            executor = TerminalExecutor()
            line_number = 0
            error_count = 0
            
            try:
                # Use interactive mode if input_lines provided, otherwise use streaming
                if input_lines:
                    execution_stream = executor.execute_with_input(code, input_lines)
                else:
                    execution_stream = executor.execute_streaming(code)
                
                # Process each execution step
                for step_event in execution_stream:
                    line_number += 1
                    step_type = step_event.get('type', 'output')
                    
                    if step_type == 'error':
                        error_count += 1
                    
                    # Create step record
                    TerminalExecutionStep.objects.create(
                        execution=execution,
                        step_type=step_type,
                        content=step_event.get('content', ''),
                        line_number=line_number,
                        execution_time_at_step=step_event.get('execution_time', 0),
                        metadata=step_event.get('metadata', {})
                    )
                
                # Update execution summary
                execution.total_lines = line_number
                execution.error_lines = error_count
                execution.execution_time = executor.execution_stats.get('end_time', 0) - executor.execution_stats.get('start_time', 0)
                execution.status = 'completed'
                execution.mark_completed()
                
            except Exception as e:
                execution.status = 'error'
                execution.save()
                
                # Log error
                TerminalExecutionStep.objects.create(
                    execution=execution,
                    step_type='error',
                    content=str(e),
                    line_number=line_number + 1,
                    metadata={'error_type': 'system'}
                )
                
                return Response({
                    'error': 'Execution failed. Please try again.',
                    'execution_id': execution.id
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Return execution summary
            final_serializer = TerminalExecutionSerializer(execution)
            return Response(final_serializer.data, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': 'Failed to create execution. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TerminalStreamingView(APIView):
    """
    Real-time streaming endpoint for terminal execution output.
    
    Returns Server-Sent Events (SSE) stream of execution output.
    Each event is a JSON object with execution step data.
    
    Usage:
        POST /api/compiler/terminal/stream/
        {
            "code": "for i in range(5): print(i)",
            "language": "python"
        }
        
    Events emitted:
        - step: Execution started/milestone
        - output: Standard output line
        - error: Error output line  
        - input: User input echo
        - status: Status update
        - summary: Execution complete with stats
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Stream code execution output in real-time."""
        from django.http import StreamingHttpResponse
        
        serializer = TerminalExecutionCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        language = serializer.validated_data.get('language', 'python')
        input_lines = serializer.validated_data.get('input_lines', [])
        
        # Create execution record
        execution = TerminalExecution.objects.create(
            user=request.user,
            code=code,
            language=language,
            status='running'
        )
        
        def event_stream():
            """Generate SSE events for each execution step."""
            import json
            
            executor = TerminalExecutor()
            line_number = 0
            error_count = 0
            
            try:
                if input_lines:
                    execution_stream = executor.execute_with_input(code, input_lines)
                else:
                    execution_stream = executor.execute_streaming(code)
                
                for step_event in execution_stream:
                    line_number += 1
                    step_type = step_event.get('type', 'output')
                    
                    if step_type == 'error':
                        error_count += 1
                    
                    # Create step record
                    TerminalExecutionStep.objects.create(
                        execution=execution,
                        step_type=step_type,
                        content=step_event.get('content', ''),
                        line_number=line_number,
                        execution_time_at_step=step_event.get('execution_time', 0),
                        metadata=step_event.get('metadata', {})
                    )
                    
                    # Yield as SSE event
                    event_data = {
                        'id': line_number,
                        'type': step_type,
                        'content': step_event.get('content', ''),
                        'line_number': line_number,
                        'execution_time': step_event.get('execution_time', 0),
                        'execution_id': execution.id,
                        'metadata': step_event.get('metadata', {})
                    }
                    
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                # Update execution summary
                execution.total_lines = line_number
                execution.error_lines = error_count
                execution.execution_time = executor.execution_stats.get('end_time', 0) - executor.execution_stats.get('start_time', 0)
                execution.status = 'completed'
                execution.mark_completed()
                
                # Final summary event
                summary_data = {
                    'type': 'completed',
                    'execution_id': execution.id,
                    'total_lines': line_number,
                    'error_lines': error_count,
                    'execution_time': execution.execution_time,
                    'status': 'completed'
                }
                yield f"data: {json.dumps(summary_data)}\n\n"
            
            except Exception as e:
                execution.status = 'error'
                execution.save()
                
                error_data = {
                    'type': 'error',
                    'content': str(e),
                    'execution_id': execution.id,
                    'error_type': 'system'
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )


# ══════════════════════════════════════════════════════════════════════════════
# AST Analysis Views - Real-time code analysis
# ══════════════════════════════════════════════════════════════════════════════

class ASTAnalysisView(APIView):
    """
    Real-time AST analysis endpoint.
    Returns diagnostics, complexity metrics, and refactoring suggestions.
    
    Usage:
        POST /api/compiler/analyze/
        {
            "code": "def foo(): ...",
            "language": "python"
        }
        
    Response:
        {
            "issues": [...],
            "metrics": {...},
            "dependencies": [...],
            "exports": [...],
            "astValid": true,
            "parseError": null
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '')
        language = request.data.get('language', 'python')
        line_number = request.data.get('line')  # Optional: analyze specific line

        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Enforce code size limit
        max_code_size = getattr(settings, 'MAX_CODE_SIZE', 1000000)
        if len(code) > max_code_size:
            return Response(
                {'error': f'Code exceeds maximum size of {max_code_size} characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if language == 'python':
            parser = PythonParser()
            if line_number is not None:
                issues = parser.analyze_line(code, line_number)
                result = {
                    'issues': [i.to_dict() for i in issues],
                    'line': line_number,
                }
            else:
                analysis = parser.analyze(code)
                result = analysis.to_dict()
        else:
            # For non-Python languages, return basic info
            result = {
                'issues': [],
                'metrics': {
                    'linesOfCode': len(code.split('\n')),
                    'logicalLines': len([l for l in code.split('\n') if l.strip()]),
                },
                'dependencies': [],
                'exports': [],
                'astValid': True,
                'parseError': None,
                'note': f'AST analysis not yet supported for {language}',
            }

        return Response(result, status=status.HTTP_200_OK)


class CodeMetricsView(APIView):
    """
    Quick metrics endpoint for a code file.
    Returns only complexity metrics without full analysis.
    
    Usage:
        POST /api/compiler/metrics/
        {
            "code": "def foo(): ...",
            "language": "python"
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get('code', '')
        language = request.data.get('language', 'python')

        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if language == 'python':
            analysis = analyze_python_code(code)
            result = {
                'metrics': analysis.metrics.to_dict(),
                'issueCount': len(analysis.issues),
                'errorCount': sum(1 for i in analysis.issues if i.severity.value == 'error'),
                'warningCount': sum(1 for i in analysis.issues if i.severity.value == 'warning'),
            }
        else:
            result = {
                'metrics': {
                    'linesOfCode': len(code.split('\n')),
                },
                'issueCount': 0,
                'errorCount': 0,
                'warningCount': 0,
            }

        return Response(result, status=status.HTTP_200_OK)


class GroqPoolStatusView(APIView):
    """View Groq API key pool status — available keys, usage stats, capacity."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.compiler.groq_key_pool import get_groq_pool

        pool = get_groq_pool()
        # Do NOT call load_from_env() here — it resets all usage counters!
        # Keys are loaded once at startup via get_groq_pool()

        return Response({
            'total_keys': len(pool.keys),
            'available_keys': pool.get_available_count(),
            'total_rpd_capacity': pool.get_total_rpd_capacity(),
            'keys': pool.get_stats(),
        }, status=status.HTTP_200_OK)


class SQLSchemaView(APIView):
    """Return the current live schema of the in-memory SQL database."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.compiler.executor import SQLExecutor
        schema = SQLExecutor.get_schema()
        return Response({'tables': schema}, status=status.HTTP_200_OK)


class SQLResetView(APIView):
    """Reset the in-memory SQL database — drop all user tables and re-seed."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.compiler.executor import SQLExecutor
        SQLExecutor.reset()
        return Response({'status': 'ok', 'message': 'Database reset to default tables'}, status=status.HTTP_200_OK)

