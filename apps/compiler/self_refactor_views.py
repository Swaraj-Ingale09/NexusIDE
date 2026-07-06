"""
Self-Refactoring API Endpoints
Allows NexusIDE to analyze and improve its own code
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from django.conf import settings
import os
import logging

from .self_refactor import get_refactoring_engine

logger = logging.getLogger(__name__)


class CodeAnalysisView(APIView):
    """Analyze code quality of a file or directory"""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """
        Analyze code quality
        
        Request:
        {
            "filepath": "optional specific file",
            "directory": "optional directory (defaults to project root)",
            "exclude_dirs": ["__pycache__", "venv"]
        }
        """
        try:
            filepath = request.data.get('filepath')
            directory = request.data.get('directory')
            exclude_dirs = request.data.get('exclude_dirs', ['venv', '__pycache__', '.git'])
            
            engine = get_refactoring_engine(settings.BASE_DIR)
            
            if filepath:
                # Analyze single file
                analysis = engine.analyzer.analyze_file(filepath)
                return Response({
                    'success': True,
                    'type': 'single_file',
                    'analysis': analysis,
                }, status=status.HTTP_200_OK)
            
            else:
                # Analyze directory
                target_dir = directory or str(settings.BASE_DIR)
                analysis = engine.analyze_directory(target_dir, exclude_dirs)
                
                return Response({
                    'success': True,
                    'type': 'directory',
                    'analysis': analysis,
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Code analysis error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AutoRefactorView(APIView):
    """Automatically refactor code"""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """
        Auto-refactor code
        
        Request:
        {
            "filepath": "path/to/file.py",
            "apply_changes": true,
            "preview_only": false
        }
        """
        try:
            filepath = request.data.get('filepath')
            apply_changes = request.data.get('apply_changes', False)
            
            if not filepath:
                return Response(
                    {'error': 'filepath is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Security check - ensure file is within project
            base_path = str(settings.BASE_DIR)
            real_path = os.path.realpath(filepath)
            if not real_path.startswith(base_path):
                return Response(
                    {'error': 'File path outside project directory'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            engine = get_refactoring_engine(settings.BASE_DIR)
            result = engine.auto_refactor_file(filepath, apply_changes)
            
            return Response({
                'success': True,
                'refactoring': result,
                'applied': apply_changes,
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Auto-refactor error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefactorDirectoryView(APIView):
    """Refactor all files in a directory"""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """
        Refactor entire directory
        
        Request:
        {
            "directory": "optional target directory",
            "apply_changes": false,
            "exclude_dirs": ["venv", "__pycache__"]
        }
        """
        try:
            directory = request.data.get('directory')
            apply_changes = request.data.get('apply_changes', False)
            
            engine = get_refactoring_engine(settings.BASE_DIR)
            result = engine.auto_refactor_directory(directory, apply_changes)
            
            return Response({
                'success': True,
                'refactoring_summary': result,
                'applied': apply_changes,
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Directory refactor error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class QualityReportView(APIView):
    """Generate comprehensive quality report"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get quality report for entire project"""
        try:
            engine = get_refactoring_engine(settings.BASE_DIR)
            report = engine.generate_quality_report()
            
            return Response({
                'success': True,
                'report': report,
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Quality report error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SelfRefactoringHistoryView(APIView):
    """View refactoring history"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get refactoring history"""
        try:
            engine = get_refactoring_engine(settings.BASE_DIR)
            
            history = {
                'total_refactorings': len(engine.refactoring_history),
                'recent': engine.refactoring_history[-50:],  # Last 50
            }
            
            return Response({
                'success': True,
                'history': history,
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"History retrieval error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CodeMetricsView(APIView):
    """Get detailed code metrics"""
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """
        Get metrics for a file or directory
        
        Request:
        {
            "filepath": "optional file path"
        }
        """
        try:
            filepath = request.data.get('filepath')
            
            engine = get_refactoring_engine(settings.BASE_DIR)
            
            if filepath:
                analysis = engine.analyzer.analyze_file(filepath)
                metrics = analysis.get('metrics', {})
                
                return Response({
                    'success': True,
                    'filepath': filepath,
                    'metrics': metrics,
                }, status=status.HTTP_200_OK)
            
            else:
                analysis = engine.analyze_directory()
                
                # Aggregate metrics
                total_lines = sum(f['metrics'].get('total_lines', 0) 
                                 for f in analysis['files'])
                total_functions = sum(f['metrics'].get('functions', 0) 
                                     for f in analysis['files'])
                total_classes = sum(f['metrics'].get('classes', 0) 
                                   for f in analysis['files'])
                
                return Response({
                    'success': True,
                    'metrics': {
                        'total_lines': total_lines,
                        'total_functions': total_functions,
                        'total_classes': total_classes,
                        'files_analyzed': analysis['files_analyzed'],
                        'average_issues_per_file': (analysis['total_issues'] / 
                                                   analysis['files_analyzed'] 
                                                   if analysis['files_analyzed'] > 0 else 0),
                    }
                }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Metrics error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IssueStatisticsView(APIView):
    """Get statistics on code issues"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get issue statistics"""
        try:
            engine = get_refactoring_engine(settings.BASE_DIR)
            report = engine.generate_quality_report()
            
            # Calculate trends
            recent_refactorings = engine.refactoring_history[-10:]
            avg_changes_recent = (sum(r.get('changes', 0) for r in recent_refactorings) / 
                                 len(recent_refactorings) if recent_refactorings else 0)
            
            return Response({
                'success': True,
                'statistics': {
                    'overall_quality': report['summary']['overall_quality_score'],
                    'total_issues': report['summary']['total_issues'],
                    'issues_by_severity': report['issues_by_severity'],
                    'top_issue_types': sorted(
                        report['issues_by_type'].items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:5],
                    'average_changes_per_refactor': round(avg_changes_recent, 2),
                    'files_analyzed': report['summary']['total_files'],
                }
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Statistics error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RecommendationsView(APIView):
    """Get improvement recommendations"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get recommended improvements"""
        try:
            engine = get_refactoring_engine(settings.BASE_DIR)
            report = engine.generate_quality_report()
            
            recommendations = []
            
            # Recommendation 1: High-severity issues
            if report['issues_by_severity']['high'] > 0:
                recommendations.append({
                    'priority': 'high',
                    'title': 'Address high-severity issues',
                    'description': f'Found {report["issues_by_severity"]["high"]} high-severity issues',
                    'action': 'Run auto-refactor to fix critical issues',
                    'impact': 'Significantly improves code quality'
                })
            
            # Recommendation 2: Low quality files
            low_quality_files = [f for f in report['files'] if f['quality_score'] < 60]
            if low_quality_files:
                recommendations.append({
                    'priority': 'medium',
                    'title': 'Refactor low-quality files',
                    'description': f'Found {len(low_quality_files)} files with quality < 60',
                    'action': 'Focus on files: ' + ', '.join([f['filepath'][-30:] 
                                                             for f in low_quality_files[:3]]),
                    'impact': 'Improves maintainability'
                })
            
            # Recommendation 3: Common issue types
            top_issues = sorted(
                report['issues_by_type'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            if top_issues:
                recommendations.append({
                    'priority': 'low',
                    'title': 'Address recurring issues',
                    'description': f'Most common issue: {top_issues[0][0]} ({top_issues[0][1]} occurrences)',
                    'action': f'Consider creating patterns to prevent {top_issues[0][0]}',
                    'impact': 'Prevents future quality degradation'
                })
            
            return Response({
                'success': True,
                'recommendations': recommendations,
                'overall_score': report['summary']['overall_quality_score'],
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Recommendations error: {str(e)}")
            return Response(
                {'error': 'Request failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
