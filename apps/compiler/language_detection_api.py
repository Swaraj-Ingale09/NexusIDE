"""
Language Detection API Endpoints
Auto-detect and execute code in any supported language
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import logging
import time

from apps.compiler.language_detector import LanguageDetector
from apps.compiler.executor import execute_code

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def detect_language_api(request):
    """
    Detect programming language from code
    POST /api/compiler/detect-language/
    
    Request:
    {
        "code": "python code or c++ code or javascript...",
        "filename": "optional filename.py"
    }
    
    Response:
    {
        "success": true,
        "language": "python",
        "confidence": 5,
        "info": {
            "name": "Python",
            "icon": "🐍",
            "description": "..."
        }
    }
    """
    try:
        code = request.data.get('code', '').strip()
        filename = request.data.get('filename', '')
        
        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Detect language
        detected_lang = LanguageDetector.detect(code, filename)
        lang_info = LanguageDetector.get_language_info(detected_lang)
        
        return Response({
            'success': True,
            'language': detected_lang,
            'info': lang_info,
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Language detection error: {str(e)}")
        return Response(
            {'error': 'Language detection failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_execute_code_api(request):
    """
    Execute code with auto-detected language
    POST /api/compiler/auto-execute/
    
    Request:
    {
        "code": "your code here",
        "stdin": "optional input",
        "filename": "optional filename.py"
    }
    
    Response:
    {
        "success": true,
        "language": "python",
        "output": "...",
        "error": "",
        "status": "success",
        "execution_time": 0.123
    }
    """
    try:
        import os
        from apps.compiler.models import ExecutionHistory
        
        code = request.data.get('code', '').strip()
        stdin = request.data.get('stdin', '')
        filename = request.data.get('filename', '')
        
        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        start_time = time.time()
        
        # Auto-detect language
        language = LanguageDetector.detect(code, filename)
        logger.info(f"Auto-detected language: {language}")
        
        # Execute code
        result = execute_code(code, language=language, stdin=stdin)
        execution_time = time.time() - start_time
        
        # Save to database if user is authenticated
        if request.user.is_authenticated:
            try:
                ExecutionHistory.objects.create(
                    user=request.user,
                    code=code,
                    output=result['output'],
                    error=result['error'],
                    status=result['status'],
                    execution_time=result['execution_time'],
                    stdin=stdin,
                    metadata={
                        "artifacts": result.get('artifacts', []),
                        "language": language,
                        "auto_detected": True
                    },
                )
            except Exception as e:
                logger.error(f"Error saving execution history: {e}")
        
        return Response({
            'success': result['status'] == 'success',
            'language': language,
            'output': result['output'],
            'error': result['error'],
            'status': result['status'],
            'execution_time': result['execution_time'],
            'artifacts': result.get('artifacts', []),
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Auto-execute error: {str(e)}")
        return Response(
            {'error': 'Execution failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def supported_languages_api(request):
    """
    Get list of supported languages
    GET /api/compiler/supported-languages/
    
    Response:
    {
        "success": true,
        "languages": [
            {
                "name": "Python",
                "id": "python",
                "icon": "🐍",
                "description": "..."
            },
            ...
        ]
    }
    """
    try:
        languages = []
        
        for lang in LanguageDetector.get_supported_languages():
            info = LanguageDetector.get_language_info(lang)
            languages.append({
                'id': lang,
                'name': info.get('name', lang),
                'icon': info.get('icon', '💻'),
                'description': info.get('description', ''),
                'extensions': info.get('extensions', []),
            })
        
        return Response({
            'success': True,
            'languages': languages,
            'count': len(languages),
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Supported languages error: {str(e)}")
        return Response(
            {'error': 'Request failed. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class LanguageDetectionView(APIView):
    """Multi-function language detection and execution"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Multi-purpose endpoint
        
        POST /api/compiler/language/
        
        Actions:
        - "detect" - Detect language only
        - "execute" - Detect and execute
        
        Request:
        {
            "action": "detect",
            "code": "...",
            "filename": "optional"
        }
        """
        try:
            action = request.data.get('action', 'execute').lower()
            code = request.data.get('code', '').strip()
            filename = request.data.get('filename', '')
            
            if not code:
                return Response(
                    {'error': 'Code is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if action == 'detect':
                language = LanguageDetector.detect(code, filename)
                lang_info = LanguageDetector.get_language_info(language)
                
                return Response({
                    'success': True,
                    'action': 'detect',
                    'language': language,
                    'info': lang_info,
                }, status=status.HTTP_200_OK)
            
            elif action == 'execute':
                stdin = request.data.get('stdin', '')
                language = LanguageDetector.detect(code, filename)
                result = execute_code(code, language=language, stdin=stdin)
                
                return Response({
                    'success': result['status'] == 'success',
                    'action': 'execute',
                    'language': language,
                    'output': result['output'],
                    'error': result['error'],
                    'status': result['status'],
                    'execution_time': result['execution_time'],
                    'artifacts': result.get('artifacts', []),
                }, status=status.HTTP_200_OK)
            
            else:
                return Response(
                    {'error': f'Unknown action: {action}. Use "detect" or "execute"'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            logger.error(f"Language detection error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
