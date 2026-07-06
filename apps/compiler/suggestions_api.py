"""
In-Line Suggestions API using OpenRouter & Nvidia NIM
Fast, production-ready endpoints
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

from apps.compiler.ai_providers import get_multi_provider_ai
from apps.compiler.inline_suggestions import get_inline_suggestions, apply_all_inline_suggestions

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_fix_api(request):
    """
    Quick fix - Auto-fix code using AI + Cache
    POST /api/suggestions/quick-fix/
    
    Request: {"code": "buggy code", "error": "optional error"}
    Response: {"success": true, "fixed_code": "...", "provider": "openrouter", "cached": false}
    """
    try:
        import time
        from apps.compiler.ai_cache import AIQueryCache
        
        code = request.data.get('code', '').strip()
        error = request.data.get('error', '')
        
        if not code:
            return Response(
                {'error': 'Code required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_time = time.time()
        
        # Check cache first
        cached_results = AIQueryCache.get_similar_responses(code, 'fix', limit=1)
        if cached_results:
            execution_time = time.time() - start_time
            cached_result = cached_results[0]
            logger.info(f"Returning cached result for {request.user}")
            return Response({
                'success': True,
                'fixed_code': cached_result.response_output,
                'provider': cached_result.provider,
                'type': 'auto_fix',
                'cached': True,
                'cached_from': cached_result.created_at.isoformat(),
                'execution_time': execution_time
            }, status=status.HTTP_200_OK)
        
        # If not cached, call real API
        ai = get_multi_provider_ai()
        result = ai.auto_fix(code, error)
        
        execution_time = time.time() - start_time
        
        # Save to database for future cache hits
        try:
            user = request.user if request.user.is_authenticated else None
            AIQueryCache.save_query(
                user=user,
                action='fix',
                query_input=code,
                response_output=result['fixed_code'],
                provider=result['provider'],
                status='success' if result['success'] else 'failed',
                execution_time=execution_time
            )
        except Exception as e:
            logger.error(f"Error saving query to cache: {e}")
        
        return Response({
            'success': result['success'],
            'fixed_code': result['fixed_code'],
            'provider': result['provider'],
            'type': 'auto_fix',
            'cached': False,
            'execution_time': execution_time
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Quick fix error: {str(e)}")
        return Response({'error': 'Processing failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_explain_api(request):
    """
    Quick explain - Explain code snippet
    POST /api/suggestions/quick-explain/
    
    Request: {"code": "..."}
    Response: {"explanation": "...", "provider": "nvidia"}
    """
    try:
        code = request.data.get('code', '').strip()
        
        if not code:
            return Response(
                {'error': 'Code required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ai = get_multi_provider_ai()
        result = ai.explain_inline(code)
        
        return Response({
            'success': result['success'],
            'explanation': result['explanation'],
            'provider': result['provider'],
            'type': 'explain'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Quick explain error: {str(e)}")
        return Response({'error': 'Processing failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_optimize_api(request):
    """
    Quick optimize - Optimize code
    POST /api/suggestions/quick-optimize/
    
    Request: {"code": "..."}
    Response: {"suggestion": "...", "provider": "openrouter"}
    """
    try:
        code = request.data.get('code', '').strip()
        
        if not code:
            return Response(
                {'error': 'Code required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ai = get_multi_provider_ai()
        result = ai.optimize_inline(code)
        
        return Response({
            'success': result['success'],
            'suggestion': result['suggestion'],
            'provider': result['provider'],
            'type': 'optimize'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Quick optimize error: {str(e)}")
        return Response({'error': 'Processing failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_review_api(request):
    """
    Quick review - Code review
    POST /api/suggestions/quick-review/
    
    Request: {"code": "..."}
    Response: {"review": "...", "provider": "nvidia"}
    """
    try:
        code = request.data.get('code', '').strip()
        
        if not code:
            return Response(
                {'error': 'Code required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ai = get_multi_provider_ai()
        result = ai.review_inline(code)
        
        return Response({
            'success': result['success'],
            'review': result['review'],
            'provider': result['provider'],
            'type': 'review'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Quick review error: {str(e)}")
        return Response({'error': 'Processing failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def quick_suggest_api(request):
    """
    Quick suggest - General suggestions
    POST /api/suggestions/quick-suggest/
    
    Request: {"code": "..."}
    Response: {"improvements": "...", "provider": "openrouter"}
    """
    try:
        code = request.data.get('code', '').strip()
        
        if not code:
            return Response(
                {'error': 'Code required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ai = get_multi_provider_ai()
        result = ai.suggest_improvements(code)
        
        return Response({
            'success': result['success'],
            'improvements': result['improvements'],
            'provider': result['provider'],
            'type': 'suggestions'
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Quick suggest error: {str(e)}")
        return Response({'error': 'Processing failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_code_api(request):
    """
    ChatGPT-like code generation with caching
    POST /api/suggestions/generate/
    
    Request: {"prompt": "Write a function that..."}
    Response: {"success": true, "generated_code": "...", "provider": "openrouter", "cached": false}
    """
    try:
        import time
        from apps.compiler.ai_cache import AIQueryCache
        
        prompt = request.data.get('prompt', '').strip()
        
        if not prompt:
            return Response(
                {'error': 'Prompt required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(prompt) < 5:
            return Response(
                {'error': 'Prompt too short (minimum 5 characters)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(prompt) > 5000:
            return Response(
                {'error': 'Prompt too long (maximum 5000 characters)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_time = time.time()
        
        # Check cache first
        cached_results = AIQueryCache.get_similar_responses(prompt, 'generate', limit=1)
        if cached_results:
            execution_time = time.time() - start_time
            cached_result = cached_results[0]
            logger.info(f"Returning cached generated code for {request.user}")
            return Response({
                'success': True,
                'generated_code': cached_result.response_output,
                'provider': cached_result.provider,
                'type': 'generate',
                'cached': True,
                'cached_from': cached_result.created_at.isoformat(),
                'execution_time': execution_time
            }, status=status.HTTP_200_OK)
        
        # If not cached, call real API
        ai = get_multi_provider_ai()
        result = ai.generate_code(prompt)
        
        execution_time = time.time() - start_time
        
        if not result['success']:
            return Response(
                {'error': 'Failed to generate code. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Save to database for future cache hits
        try:
            user = request.user if request.user.is_authenticated else None
            AIQueryCache.save_query(
                user=user,
                action='generate',
                query_input=prompt,
                response_output=result['generated_code'],
                provider=result['provider'],
                status='success' if result['success'] else 'failed',
                execution_time=execution_time
            )
        except Exception as e:
            logger.error(f"Error saving query to cache: {e}")
        
        return Response({
            'success': result['success'],
            'generated_code': result['generated_code'],
            'provider': result['provider'],
            'type': 'generate',
            'cached': False,
            'execution_time': execution_time
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Generate code error: {str(e)}")
        return Response({'error': 'Processing failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def smart_suggestions_api(request):
    """
    Smart suggestions - Rule-based + AI suggestions
    POST /api/suggestions/smart/
    
    Combines fast rule-based suggestions with AI for best results
    """
    try:
        code = request.data.get('code', '').strip()
        line_num = request.data.get('line')
        
        if not code:
            return Response(
                {'error': 'Code required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get rule-based suggestions (fast)
        rules_suggestions = get_inline_suggestions(code, line_num)
        
        # Get AI suggestions (slower but better)
        ai = get_multi_provider_ai()
        ai_result = ai.suggest_improvements(code)
        
        return Response({
            'success': True,
            'rules_suggestions': rules_suggestions,
            'ai_suggestions': ai_result['improvements'] if ai_result['success'] else None,
            'ai_provider': ai_result['provider'],
            'total_suggestions': len(rules_suggestions)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Smart suggestions error: {str(e)}")
        return Response({'error': 'Processing failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CodeAssistantView(APIView):
    """Complete code assistant with all features"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Multi-function code assistant
        POST /api/assistant/
        
        Actions: fix, explain, optimize, review, suggest, generate
        """
        try:
            action = request.data.get('action', 'suggest').lower()
            code = request.data.get('code', '').strip()
            prompt = request.data.get('prompt', '').strip()
            
            # For generate action, use prompt instead of code
            if action == 'generate':
                if not prompt:
                    return Response(
                        {'error': 'Prompt required for generate action'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif not code:
                return Response(
                    {'error': 'Code required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            ai = get_multi_provider_ai()
            
            if action == 'fix':
                result = ai.auto_fix(code, request.data.get('error', ''))
            elif action == 'explain':
                result = ai.explain_inline(code)
            elif action == 'optimize':
                result = ai.optimize_inline(code)
            elif action == 'review':
                result = ai.review_inline(code)
            elif action == 'generate':
                result = ai.generate_code(prompt)
            elif action == 'suggest':
                result = ai.suggest_improvements(code)
            else:
                result = {'success': False, 'improvements': 'Unknown action'}
            
            return Response({
                'success': result['success'],
                'action': action,
                'result': result,
                'provider': result.get('provider', 'unknown')
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Code assistant error: {str(e)}")
            return Response({'error': 'Processing failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
