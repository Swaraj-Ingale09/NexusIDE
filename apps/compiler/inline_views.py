"""
In-Line Suggestions API Views
Real-time code suggestions as user types
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import logging

from apps.compiler.inline_suggestions import (
    get_inline_suggestions,
    apply_inline_suggestion,
    apply_all_inline_suggestions
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def get_suggestions_api(request):
    """
    Get inline suggestions for code
    POST /api/suggestions/
    
    Request:
    {
        "code": "python code here",
        "line": 5  # optional - suggestions for specific line
    }
    
    Response:
    {
        "success": true,
        "suggestions": [
            {
                "type": "long_line",
                "line": 15,
                "severity": "info",
                "message": "Line is too long (88+ chars)",
                "current": "current code",
                "suggestion": "suggested fix"
            }
        ]
    }
    """
    try:
        code = request.data.get('code', '').strip()
        line_num = request.data.get('line')
        
        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        suggestions = get_inline_suggestions(code, line_num)
        
        return Response({
            'success': True,
            'suggestions': suggestions,
            'count': len(suggestions)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Suggestions error: {str(e)}")
                return Response(
            {'error': 'Request failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )






@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_suggestion_api(request):
    """
    Apply a single suggestion to code
    POST /api/suggestions/apply/
    
    Request:
    {
        "code": "original code",
        "suggestion": {
            "type": "unused_import",
            "line": 2,
            "message": "..."
        }
    }
    
    Response:
    {
        "success": true,
        "fixed_code": "code with suggestion applied"
    }
    """
    try:
        code = request.data.get('code', '').strip()
        suggestion = request.data.get('suggestion', {})
        
        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fixed_code = apply_inline_suggestion(code, suggestion)
        
        return Response({
            'success': True,
            'fixed_code': fixed_code
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Apply suggestion error: {str(e)}")
        return Response(
            {'error': 'Request failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_all_suggestions_api(request):
    """
    Apply all suggestions at once
    POST /api/suggestions/apply-all/
    
    Request:
    {
        "code": "original code",
        "suggestions": [
            {"type": "unused_import", "line": 2},
            {"type": "long_line", "line": 15}
        ]
    }
    
    Response:
    {
        "success": true,
        "fixed_code": "code with all suggestions applied",
        "applied_count": 2
    }
    """
    try:
        code = request.data.get('code', '').strip()
        suggestions = request.data.get('suggestions', [])
        
        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        fixed_code = apply_all_inline_suggestions(code, suggestions)
        
        return Response({
            'success': True,
            'fixed_code': fixed_code,
            'applied_count': len(suggestions)
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Apply all suggestions error: {str(e)}")
        return Response(
            {'error': 'Request failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class InlineSuggestionsView(APIView):
    """In-line suggestions with get/apply operations"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Multi-purpose suggestions endpoint
        POST /api/inline-suggestions/
        
        Actions:
        - "suggest" - Get suggestions
        - "apply_one" - Apply single suggestion
        - "apply_all" - Apply all suggestions
        - "preview" - Preview what will be fixed
        
        Request:
        {
            "action": "suggest",
            "code": "python code",
            "line": 5,  # optional
            "suggestion": {...}  # for apply_one
        }
        """
        try:
            action = request.data.get('action', 'suggest').lower()
            code = request.data.get('code', '').strip()
            
            if not code and action != 'preview':
                return Response(
                    {'error': 'Code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if action == 'suggest':
                # Get suggestions
                line_num = request.data.get('line')
                suggestions = get_inline_suggestions(code, line_num)
                return Response({
                    'success': True,
                    'action': 'suggest',
                    'suggestions': suggestions,
                    'count': len(suggestions)
                }, status=status.HTTP_200_OK)
            
            elif action == 'apply_one':
                # Apply single suggestion
                suggestion = request.data.get('suggestion', {})
                fixed = apply_inline_suggestion(code, suggestion)
                return Response({
                    'success': True,
                    'action': 'apply_one',
                    'fixed_code': fixed
                }, status=status.HTTP_200_OK)
            
            elif action == 'apply_all':
                # Apply all suggestions
                suggestions = request.data.get('suggestions', [])
                fixed = apply_all_inline_suggestions(code, suggestions)
                return Response({
                    'success': True,
                    'action': 'apply_all',
                    'fixed_code': fixed,
                    'applied': len(suggestions)
                }, status=status.HTTP_200_OK)
            
            elif action == 'preview':
                # Show what will be fixed
                suggestions = get_inline_suggestions(code)
                preview = {
                    'current_lines': len(code.split('\n')),
                    'issues_found': len(suggestions),
                    'fixes_available': [s['type'] for s in suggestions],
                    'summary': f"{len(suggestions)} suggestions to improve code"
                }
                return Response({
                    'success': True,
                    'action': 'preview',
                    'preview': preview
                }, status=status.HTTP_200_OK)
            
            else:
                return Response(
                    {'error': f'Unknown action: {action}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Inline suggestions error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
