"""
Auto-Fix Views
Automatically fixes code issues without manual intervention
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.conf import settings
import os
import logging

from .self_refactor import get_refactoring_engine

logger = logging.getLogger(__name__)


class AutoFixNowView(APIView):
    """Automatically fix code issues immediately"""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """
        Auto-fix code immediately
        
        Request:
        {
            "filepath": "apps/problems/models.py"  OR
            "directory": "apps/",
            "auto_commit": false,
            "fix_types": ["docstrings", "imports", "line_length", "type_hints"]
        }
        
        Returns the fixed code with detailed change log
        """
        try:
            filepath = request.data.get('filepath')
            directory = request.data.get('directory')
            auto_commit = request.data.get('auto_commit', False)
            fix_types = request.data.get('fix_types', 'all')
            
            engine = get_refactoring_engine(settings.BASE_DIR)
            
            results = {
                'success': True,
                'timestamp': str(__import__('datetime').datetime.now()),
                'files_fixed': 0,
                'total_issues_fixed': 0,
                'details': []
            }
            
            if filepath:
                # Fix single file
                result = engine.auto_refactor_file(filepath, apply_changes=True)
                
                if 'error' not in result:
                    results['files_fixed'] = 1
                    results['total_issues_fixed'] = result.get('changes_count', 0)
                    results['details'].append({
                        'filepath': filepath,
                        'changes_applied': result.get('changes_count', 0),
                        'changes': result.get('changes', []),
                        'status': 'FIXED' if result.get('applied') else 'PREVIEW'
                    })
                else:
                    return Response({
                        'error': result.get('error'),
                        'filepath': filepath
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            elif directory:
                # Fix entire directory
                result = engine.auto_refactor_directory(directory, apply_changes=True)
                
                results['files_fixed'] = result.get('files_refactored', 0)
                results['total_issues_fixed'] = result.get('total_changes', 0)
                
                for file_info in result.get('files', []):
                    results['details'].append({
                        'filepath': file_info['filepath'],
                        'changes_applied': file_info.get('changes', 0),
                        'status': 'FIXED' if file_info.get('applied') else 'PREVIEW'
                    })
            
            else:
                return Response(
                    {'error': 'filepath or directory is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Log the auto-fix operation
            logger.info(f"AutoFix: Fixed {results['files_fixed']} files, "
                       f"{results['total_issues_fixed']} issues")
            
            return Response(results, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Auto-fix error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SmartFixView(APIView):
    """Intelligently fix issues with AI suggestions"""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """
        Smart fix using AI to understand context
        
        Request:
        {
            "filepath": "apps/problems/models.py",
            "use_ai_for_refactoring": true,
            "aggressive_mode": false
        }
        """
        try:
            filepath = request.data.get('filepath')
            use_ai = request.data.get('use_ai_for_refactoring', False)
            aggressive = request.data.get('aggressive_mode', False)
            
            if not filepath:
                return Response(
                    {'error': 'filepath is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Security check
            base_path = str(settings.BASE_DIR)
            real_path = os.path.realpath(filepath)
            if not real_path.startswith(base_path):
                return Response(
                    {'error': 'File path outside project directory'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            engine = get_refactoring_engine(settings.BASE_DIR)
            
            # 1. Analyze
            analysis = engine.analyzer.analyze_file(filepath)
            
            # 2. Refactor
            refactoring = engine.auto_refactor_file(filepath, apply_changes=True)
            
            # 3. Optional AI enhancement
            ai_suggestions = []
            if use_ai and 'error' not in analysis:
                # Try to get AI suggestions for complex issues
                from .ai_service import get_ai_service
                ai_service = get_ai_service()
                
                # Get original code for AI review
                with open(filepath, 'r') as f:
                    code = f.read()
                
                # Ask AI for additional improvements
                ai_result = ai_service.analyzer.refactor_code(code, 'extract_functions')
                if 'refactored_code' in ai_result:
                    ai_suggestions = ai_result.get('changes', [])
            
            return Response({
                'success': True,
                'filepath': filepath,
                'automatic_fixes': {
                    'count': refactoring.get('changes_count', 0),
                    'changes': refactoring.get('changes', []),
                    'applied': True
                },
                'ai_suggestions': ai_suggestions if use_ai else [],
                'quality_score_before': analysis.get('quality_score', 0),
                'refactored': True
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Smart fix error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContinuousFixView(APIView):
    """Continuously fix issues in the background"""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """
        Enable continuous fixing mode
        
        Request:
        {
            "enabled": true,
            "directory": "apps/",
            "interval_minutes": 60,
            "auto_apply": true
        }
        """
        try:
            enabled = request.data.get('enabled', True)
            directory = request.data.get('directory', str(settings.BASE_DIR))
            interval = request.data.get('interval_minutes', 60)
            auto_apply = request.data.get('auto_apply', True)
            
            # Store configuration (in production, use cache or database)
            import django.core.cache as cache_module
            cache = cache_module.cache
            
            config = {
                'enabled': enabled,
                'directory': directory,
                'interval': interval,
                'auto_apply': auto_apply,
                'last_run': str(__import__('datetime').datetime.now())
            }
            
            cache.set('continuous_fix_config', config, timeout=None)
            
            if enabled:
                # Run immediate fix
                engine = get_refactoring_engine(settings.BASE_DIR)
                result = engine.auto_refactor_directory(directory, apply_changes=auto_apply)
                
                message = f"Continuous fixing enabled. Fixed {result.get('files_refactored', 0)} files."
            else:
                message = "Continuous fixing disabled."
            
            return Response({
                'success': True,
                'message': message,
                'config': config
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Continuous fix error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QuickFixView(APIView):
    """One-click fix for all issues"""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """
        Fix all issues in entire project with one command
        
        Request:
        {
            "scope": "entire" OR "apps" OR "specific",
            "path": "optional path for specific scope",
            "preserve_logic": true,
            "create_backup": true
        }
        """
        try:
            scope = request.data.get('scope', 'apps')
            custom_path = request.data.get('path')
            preserve_logic = request.data.get('preserve_logic', True)
            create_backup = request.data.get('create_backup', True)
            
            # Determine target directory
            if scope == 'entire':
                target_dir = str(settings.BASE_DIR)
            elif scope == 'apps':
                target_dir = os.path.join(settings.BASE_DIR, 'apps')
            elif scope == 'specific' and custom_path:
                target_dir = custom_path
            else:
                target_dir = os.path.join(settings.BASE_DIR, 'apps')
            
            # Create backup if requested
            backup_info = None
            if create_backup:
                import shutil
                backup_dir = f"{target_dir}_backup_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copytree(target_dir, backup_dir)
                backup_info = backup_dir
                logger.info(f"Backup created: {backup_dir}")
            
            # Run auto-refactoring
            engine = get_refactoring_engine(settings.BASE_DIR)
            
            # Get analysis first
            analysis = engine.analyze_directory(target_dir)
            
            # Apply fixes
            result = engine.auto_refactor_directory(target_dir, apply_changes=True)
            
            # Get post-fix analysis
            post_analysis = engine.analyze_directory(target_dir)
            
            return Response({
                'success': True,
                'summary': {
                    'scope': scope,
                    'target': target_dir,
                    'files_fixed': result.get('files_refactored', 0),
                    'total_changes': result.get('total_changes', 0),
                    'quality_improvement': post_analysis['quality_score'] - analysis['quality_score']
                },
                'before': {
                    'quality_score': analysis['quality_score'],
                    'total_issues': analysis['total_issues'],
                    'files_analyzed': analysis['files_analyzed']
                },
                'after': {
                    'quality_score': post_analysis['quality_score'],
                    'total_issues': post_analysis['total_issues'],
                    'files_analyzed': post_analysis['files_analyzed']
                },
                'backup': backup_info if create_backup else None,
                'message': f"✅ Fixed {result['files_refactored']} files with {result['total_changes']} changes. "
                          f"Quality improved from {analysis['quality_score']:.1f} to {post_analysis['quality_score']:.1f}"
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Quick fix error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
