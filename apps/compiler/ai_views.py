"""
AI Integration Views
Exposes AI features via REST API
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import models
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from apps.compiler.models import CodeSnippet, ExecutionHistory
from apps.users.models import UserActivity
from config.rate_limiter import rate_limit, EXECUTION_LIMITER, get_client_identifier
from .ai_service import get_ai_service
from .ai_robust_service import RobustAIService
from .ai_proactive_service import ProactiveAIService
from .prompt_guard import get_injection_protector
import logging
import json

logger = logging.getLogger(__name__)

# Initialize prompt injection protector
_injection_protector = get_injection_protector()


@method_decorator(csrf_exempt, name='dispatch')
class AIStreamView(APIView):
    """
    Server-Sent Events streaming endpoint for the AI chat panel.
    POST /api/ai/stream/
    Body: { "action": "explain|fix|optimize|format|test|chat",
            "code": "...", "context": "..." }
    Streams text chunks as SSE: data: <chunk>\n\n
    Ends with:                  data: [DONE]\n\n
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        try:
            body    = json.loads(request.body)
            action  = body.get('action', 'explain').lower()
            code    = body.get('code', '').strip()
            context = body.get('context', '').strip()
            output  = body.get('execution_output') or body.get('output') or ''
            error   = body.get('execution_error') or body.get('error_output') or body.get('stderr') or body.get('error') or ''
        except (json.JSONDecodeError, Exception):
            action  = request.POST.get('action', 'explain')
            code    = request.POST.get('code', '')
            context = request.POST.get('context', '')
            output  = request.POST.get('execution_output') or request.POST.get('output') or ''
            error   = request.POST.get('execution_error') or request.POST.get('error_output') or request.POST.get('stderr') or request.POST.get('error') or ''

        # Prompt injection protection on context
        if context:
            safe_context, is_suspicious, reason = _injection_protector.sanitize_for_ai(
                context, code_context=code
            )
            if is_suspicious:
                logger.warning(
                    "Prompt injection blocked on AI stream: reason=%s",
                    reason
                )
                context = safe_context

        from apps.compiler.ai_providers import get_multi_provider_ai
        ai = get_multi_provider_ai()

        def event_stream():
            extra = context
            if output:
                extra = (extra + '\n\n' if extra else '') + f"Execution output:\n{output}"
            if error:
                extra = (extra + '\n\n' if extra else '') + f"Execution error:\n{error}"

            try:
                for chunk in ai.stream_action(action, code, extra):
                    # Escape newlines inside the chunk so SSE framing stays intact
                    safe = chunk.replace('\n', '\\n')
                    yield f"data: {safe}\n\n"
            except Exception as e:
                yield f"data: [ERROR] {str(e)}\n\n"
            finally:
                yield "data: [DONE]\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response




class AIAssistantView(APIView):
    """Main AI Assistant endpoint with multiple capabilities"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Process code with AI
        
        Request body:
        {
            "code": "python code here",
            "action": "fix|explain|optimize|test|refactor|debug|review|chat",
            "error": "optional error message",
            "test_failures": ["optional", "test failures"],
            "optimization_goal": "speed|memory|readability",
            "debug_traceback": "optional traceback",
            "review_focus": ["performance", "security"],
            "chat_messages": [{"role": "user", "content": "message"}]
        }
        """
        try:
            code = request.data.get('code', '').strip()
            action = request.data.get('action', 'explain').lower()
            context = request.data.get('context', '')
            
            if not code:
                return Response(
                    {'error': 'Code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if len(code) > 50000:
                return Response(
                    {'error': 'Code too large (max 50KB)'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Prompt injection protection on user context/messages
            if context:
                safe_context, is_suspicious, reason = _injection_protector.sanitize_for_ai(
                    context, code_context=code
                )
                if is_suspicious:
                    logger.warning(
                        "Prompt injection blocked on AI endpoint: user=%s reason=%s",
                        request.user.username if request.user.is_authenticated else 'anon',
                        reason
                    )
                    context = safe_context

            # Check chat messages for injection
            chat_messages = request.data.get('chat_messages', [])
            if chat_messages:
                for msg in chat_messages:
                    if msg.get('content'):
                        safe_content, is_suspicious, _ = _injection_protector.sanitize_for_ai(
                            msg['content'], code_context=code
                        )
                        if is_suspicious:
                            msg['content'] = safe_content
            
            # Get AI service
            ai_service = get_ai_service()
            
            # Prepare kwargs based on action
            kwargs = {}
            
            if action == 'fix':
                kwargs['error'] = request.data.get('error')
                kwargs['test_failures'] = request.data.get('test_failures')
                kwargs['execution_output'] = request.data.get('execution_output') or request.data.get('output')
                kwargs['execution_error'] = request.data.get('execution_error') or request.data.get('error_output') or request.data.get('stderr')
            
            elif action == 'optimize':
                kwargs['optimization_goal'] = request.data.get('optimization_goal')
            
            elif action == 'debug':
                kwargs['error'] = request.data.get('error', 'Unknown error')
                kwargs['traceback'] = request.data.get('debug_traceback')
                kwargs['execution_output'] = request.data.get('execution_output') or request.data.get('output')
                kwargs['execution_error'] = request.data.get('execution_error') or request.data.get('error_output') or request.data.get('stderr')
            
            elif action == 'explain':
                base_context = request.data.get('context', '')
                execution_output = request.data.get('execution_output') or request.data.get('output')
                execution_error = request.data.get('execution_error') or request.data.get('error_output') or request.data.get('stderr')
                combined_context = base_context
                if execution_output:
                    combined_context += ('\n\n' if combined_context else '') + f"Execution output:\n{execution_output}"
                if execution_error:
                    combined_context += ('\n\n' if combined_context else '') + f"Execution error:\n{execution_error}"
                if combined_context:
                    kwargs['context'] = combined_context
            
            elif action == 'refactor':
                kwargs['refactoring_type'] = request.data.get('refactoring_type')
            
            elif action == 'review':
                kwargs['review_focus'] = request.data.get('review_focus', [])
            
            elif action == 'chat':
                kwargs['messages'] = request.data.get('chat_messages', [])
                kwargs['code_context'] = code
            
            # Process with AI
            result = ai_service.process_code(code, action, **kwargs)
            
            # Log activity if authenticated
            if request.user.is_authenticated:
                UserActivity.objects.create(
                    user=request.user,
                    activity_type='ai_chat',
                    description=f"AI {action}: {code[:100]}..."
                )
            
            return Response({
                'success': True,
                'action': action,
                'result': result
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"AI Assistant error: {str(e)}")
            return Response(
                {'error': 'AI processing failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AutoFixView(APIView):
    """Dedicated auto-fix endpoint with proactive error prevention"""
    permission_classes = [IsAuthenticated]
    
    @rate_limit(EXECUTION_LIMITER)
    def post(self, request):
        """
        Auto-fix code with proactive error prevention
        
        Request:
        {
            "code": "buggy code",
            "language": "python|c|cpp",
            "error": "error message",
            "create_snippet": true
        }
        
        Response:
        {
            "success": bool,
            "fixed_code": str,
            "method": "proactive|robust",
            "attempts": int,
            "explanation": str,
            "confidence": float
        }
        """
        try:
            code = request.data.get('code', '').strip()
            language = request.data.get('language', 'python').lower()
            error = request.data.get('error', '')
            execution_output = request.data.get('execution_output') or request.data.get('output')
            execution_error = request.data.get('execution_error') or request.data.get('error_output') or request.data.get('stderr')
            
            if not code:
                return Response(
                    {'error': 'Code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate language
            if language not in ['python', 'c', 'cpp', 'c++']:
                language = 'python'
            
            # TRY PROACTIVE SERVICE FIRST (prevents errors before they happen)
            proactive_ai = ProactiveAIService()
            result = proactive_ai.fix_code(
                code,
                error,
                language,
                execution_output=execution_output,
                execution_error=execution_error
            )
            
            # If proactive failed, use robust service as fallback
            if not result.get('success'):
                logger.info(f"Proactive fix failed, trying robust service...")
                robust_ai = RobustAIService()
                robust_result = robust_ai.fix_code(
                    code,
                    error,
                    language,
                    execution_output=execution_output,
                    execution_error=execution_error
                )
                result = robust_result
                result['method'] = 'robust'
            else:
                result['method'] = 'proactive'
            
            # Optionally save as snippet (only if successful)
            if request.data.get('create_snippet') and request.user.is_authenticated and result.get('success'):
                try:
                    snippet = CodeSnippet.objects.create(
                        user=request.user,
                        title=f"Auto-fixed code",
                        description=f"Fixed with {result.get('method')} service (attempts: {result.get('attempts')})",
                        code=result['fixed_code'],
                        language=language,
                        is_public=False,
                        tags='ai-generated,auto-fix'
                    )
                    result['snippet_id'] = snippet.id
                    result['snippet_url'] = f"/api/snippets/{snippet.id}/"
                except Exception as e:
                    logger.error(f"Failed to create snippet: {e}")
            
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Auto-fix error: {str(e)}")
            return Response(
                {'error': 'Processing failed. Please try again.', 'success': False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CodeOptimizationView(APIView):
    """Code optimization endpoint with proactive error prevention"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Optimize code with proactive error prevention
        
        Request:
        {
            "code": "code to optimize",
            "language": "python|c|cpp",
            "goal": "speed|memory|readability"
        }
        
        Response:
        {
            "success": bool,
            "optimized_code": str,
            "method": "proactive|robust",
            "attempts": int,
            "explanation": str,
            "confidence": float
        }
        """
        try:
            code = request.data.get('code', '').strip()
            language = request.data.get('language', 'python').lower()
            goal = request.data.get('goal', 'speed')
            
            if not code:
                return Response(
                    {'error': 'Code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate language
            if language not in ['python', 'c', 'cpp', 'c++']:
                language = 'python'
            
            # Validate goal
            if goal not in ['speed', 'memory', 'readability', 'performance']:
                goal = 'speed'
            
            # TRY PROACTIVE SERVICE FIRST (prevents errors before they happen)
            proactive_ai = ProactiveAIService()
            result = proactive_ai.optimize_code(code, goal, language)
            
            # If proactive failed, use robust service as fallback
            if not result.get('success'):
                logger.info(f"Proactive optimize failed, trying robust service...")
                robust_ai = RobustAIService()
                robust_result = robust_ai.optimize_code(code, goal, language)
                result = robust_result
                result['method'] = 'robust'
            else:
                result['method'] = 'proactive'
            
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Optimization error: {str(e)}")
            return Response(
                {'error': 'Processing failed. Please try again.', 'success': False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CodeExplanationView(APIView):
    """Code explanation endpoint"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Explain what code does
        
        Request:
        {
            "code": "code to explain",
            "context": "optional context"
        }
        """
        try:
            code = request.data.get('code', '').strip()
            context = request.data.get('context', '')
            
            if not code:
                return Response(
                    {'error': 'Code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            ai_service = get_ai_service()
            result = ai_service.analyzer.explain_code(code, context)
            
            return Response({
                'success': True,
                'summary': result.get('summary'),
                'detailed_explanation': result.get('detailed_explanation'),
                'key_concepts': result.get('key_concepts', []),
                'time_complexity': result.get('time_complexity'),
                'space_complexity': result.get('space_complexity'),
                'example_walkthrough': result.get('example_walkthrough'),
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Explanation error: {str(e)}")
            return Response(
                {'error': 'Processing failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TestGenerationView(APIView):
    """Generate unit tests for code"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Generate unit tests
        
        Request:
        {
            "code": "code to test",
            "function_signature": "optional function signature"
        }
        """
        try:
            code = request.data.get('code', '').strip()
            function_sig = request.data.get('function_signature', '')
            
            if not code:
                return Response(
                    {'error': 'Code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            ai_service = get_ai_service()
            result = ai_service.analyzer.generate_tests(code, function_sig)
            
            return Response({
                'success': True,
                'test_code': result.get('test_code'),
                'test_cases': result.get('test_cases', []),
                'edge_cases': result.get('edge_cases', []),
                'explanation': result.get('explanation'),
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Test generation error: {str(e)}")
            return Response(
                {'error': 'Processing failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CodeRefactoringView(APIView):
    """Code refactoring endpoint"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Refactor code for better structure
        
        Request:
        {
            "code": "code to refactor",
            "type": "extract_functions|design_patterns|clean_code"
        }
        """
        try:
            code = request.data.get('code', '').strip()
            refactor_type = request.data.get('type', None)
            
            if not code:
                return Response(
                    {'error': 'Code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            ai_service = get_ai_service()
            result = ai_service.analyzer.refactor_code(code, refactor_type)
            
            return Response({
                'success': True,
                'refactored_code': result.get('refactored_code'),
                'changes': result.get('changes', []),
                'design_patterns': result.get('design_patterns_applied', []),
                'explanation': result.get('explanation'),
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Refactoring error: {str(e)}")
            return Response(
                {'error': 'Processing failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CodeReviewView(APIView):
    """Comprehensive code review"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Review code quality
        
        Request:
        {
            "code": "code to review",
            "focus": ["performance", "security", "readability"]
        }
        """
        try:
            code = request.data.get('code', '').strip()
            focus = request.data.get('focus', [])
            
            if not code:
                return Response(
                    {'error': 'Code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            ai_service = get_ai_service()
            result = ai_service.analyzer.review_code(code, focus)
            
            return Response({
                'success': True,
                'issues': result.get('issues', []),
                'strengths': result.get('strengths', []),
                'overall_score': result.get('overall_score', 0),
                'summary': result.get('summary'),
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Code review error: {str(e)}")
            return Response(
                {'error': 'Processing failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AIChatView(APIView):
    """Multi-turn AI chat with code context - Uses OpenRouter"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Chat with AI about code - Now uses OpenRouter
        
        Request:
        {
            "messages": [{"role": "user", "content": "message"}],
            "code_context": "optional current code"
        }
        """
        try:
            from apps.compiler.ai_providers import get_multi_provider_ai
            
            messages = request.data.get('messages', [])
            code_context = request.data.get('code_context', '')
            
            if not messages:
                return Response(
                    {'error': 'Messages are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the last message from user
            last_message = messages[-1].get('content', '') if messages else ''
            
            if not last_message:
                return Response(
                    {'error': 'Last message cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Prompt injection protection on the last message
            safe_message, is_suspicious, reason = _injection_protector.sanitize_for_ai(
                last_message, code_context=code_context
            )
            if is_suspicious:
                logger.warning(
                    "Prompt injection blocked in AI chat: user=%s reason=%s",
                    request.user.username,
                    reason
                )
                last_message = safe_message
            
            # Build context for AI
            full_prompt = last_message
            if code_context:
                full_prompt = f"Code context:\n```python\n{code_context}\n```\n\nUser question: {last_message}"
            
            # Use OpenRouter to generate response
            ai = get_multi_provider_ai()
            result = ai.explain_inline(full_prompt)
            
            response_text = result['explanation'] if result['success'] else "Sorry, I couldn't generate a response. Please try again."
            
            # Log activity
            if request.user.is_authenticated:
                try:
                    UserActivity.objects.create(
                        user=request.user,
                        activity_type='ai_chat',
                        description=f"AI chat: {last_message[:100]}"
                    )
                except Exception:
                    pass  # If UserActivity doesn't exist, skip logging
            
            return Response({
                'success': result['success'],
                'response': response_text,
                'provider': result.get('provider', 'openrouter'),
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"AI chat error: {str(e)}")
            return Response(
                {'error': 'Processing failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CodeDebugView(APIView):
    """Debug code and find issues"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Debug code for errors
        
        Request:
        {
            "code": "buggy code",
            "error": "error message",
            "traceback": "optional full traceback"
        }
        """
        try:
            code = request.data.get('code', '').strip()
            error = request.data.get('error', '')
            traceback = request.data.get('traceback', '')
            
            if not code or not error:
                return Response(
                    {'error': 'Code and error message are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            ai_service = get_ai_service()
            result = ai_service.analyzer.debug_code(code, error, traceback)
            
            return Response({
                'success': True,
                'root_cause': result.get('root_cause'),
                'fixed_code': result.get('fixed_code'),
                'explanation': result.get('explanation'),
                'debugging_tips': result.get('debugging_tips', []),
                'similar_issues': result.get('similar_issues', []),
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Debug error: {str(e)}")
            return Response(
                {'error': 'Processing failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )