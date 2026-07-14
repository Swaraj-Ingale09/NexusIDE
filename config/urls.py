from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from django.http import HttpResponse, FileResponse, JsonResponse
from django.views.static import serve as static_serve
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
import os
import logging

from apps.users.views import UserViewSet, AuthViewSet, UserProfileView, UserStatsView
from apps.compiler.views import (
    CodeSnippetViewSet, ExecutionHistoryViewSet, ExecuteCodeView, AIAssistantView,
    TerminalExecutionViewSet, TerminalExecuteView, TerminalStreamingView,
    ASTAnalysisView, CodeMetricsView, GroqPoolStatusView, SQLSchemaView, SQLResetView
)
from apps.compiler.sql_ai import SQLAIView
from apps.compiler import language_detection_api
from apps.projects.views import ProjectViewSet, ProjectFileViewSet
from apps.community.views import CommunityFeedViewSet
from apps.users.health_views import HealthCheckView, DatabaseStatsView
from config.metrics import metrics_view

logger = logging.getLogger(__name__)

router = SimpleRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'code', CodeSnippetViewSet, basename='code')
router.register(r'history', ExecutionHistoryViewSet, basename='history')
router.register(r'terminal-executions', TerminalExecutionViewSet, basename='terminal-execution')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'projects/(?P<project_id>\d+)/files', ProjectFileViewSet, basename='project-file')
router.register(r'community', CommunityFeedViewSet, basename='community')

BASE_DIR = settings.BASE_DIR
REACT_DIST = os.path.join(BASE_DIR, 'static', 'dist')


def serve_react(request, *args, **kwargs):
    """Serve the React SPA index.html for all frontend routes."""
    index_path = os.path.join(REACT_DIST, 'index.html')
    if os.path.exists(index_path):
        with open(index_path, 'rb') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html')
    return HttpResponse(
        '<h1>NexusIDE</h1><p>React frontend not built yet. Run: cd frontend && npm run build</p>',
        content_type='text/html'
    )


def serve_react_asset(request, path):
    """Serve static assets from the React build."""
    file_path = os.path.join(REACT_DIST, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return static_serve(request, path, document_root=REACT_DIST)
    return HttpResponse(status=404)


def serve_root_static(request):
    """Serve root-level static files from dist (favicon, manifest, etc.)."""
    filename = request.path.lstrip('/')
    file_path = os.path.join(REACT_DIST, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return static_serve(request, filename, document_root=REACT_DIST)
    return HttpResponse(status=404)


def nexus_404(request, exception):
    """Custom 404 handler."""
    if request.path.startswith('/api/'):
        return JsonResponse({'error': 'Not found'}, status=404)
    return serve_react(request)


def nexus_500(request):
    """Custom 500 handler."""
    logger.exception("Server error on %s", request.path)
    if request.path.startswith('/api/'):
        return JsonResponse({'error': 'Internal server error'}, status=500)
    return serve_react(request)


urlpatterns = [
    path('admin/', admin.site.urls),

    # ── API Documentation ──
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='api-schema'), name='api-redoc'),

    # ── Health & System ──
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
    path('api/stats/database/', DatabaseStatsView.as_view(), name='database-stats'),
    path('metrics/', metrics_view, name='prometheus-metrics'),

    # ── REST API endpoints ──
    path('api/', include(router.urls)),
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/execute/', ExecuteCodeView.as_view(), name='execute-code'),
    path('api/sql/schema/', SQLSchemaView.as_view(), name='sql-schema'),
    path('api/sql/reset/', SQLResetView.as_view(), name='sql-reset'),
    path('api/compiler/terminal/execute/', TerminalExecuteView.as_view(), name='terminal-execute'),
    path('api/compiler/terminal/stream/', TerminalStreamingView.as_view(), name='terminal-stream'),
    path('api/ai/', AIAssistantView.as_view(), name='ai-assist'),
    path('api/sql-ai/', SQLAIView.as_view(), name='sql-ai'),
    path('api/ai/pool-status/', GroqPoolStatusView.as_view(), name='groq-pool-status'),
    path('api/ai/v2/', include('apps.compiler.ai_urls')),
    path('api/suggestions/', include('apps.compiler.suggestions_urls')),
    path('api/compiler/detect-language/', language_detection_api.detect_language_api, name='detect-language'),
    path('api/compiler/auto-execute/', language_detection_api.auto_execute_code_api, name='auto-execute'),
    path('api/compiler/supported-languages/', language_detection_api.supported_languages_api, name='supported-languages'),
    path('api/compiler/language/', language_detection_api.LanguageDetectionView.as_view(), name='language-detection'),
    path('api/compiler/analyze/', ASTAnalysisView.as_view(), name='ast-analysis'),
    path('api/compiler/metrics/', CodeMetricsView.as_view(), name='code-metrics'),
    path('api/auto-fix/', include('apps.compiler.auto_fix_urls')),
    path('api/self-refactor/', include('apps.compiler.self_refactor_urls')),
    path('api/problems/', include('apps.problems.urls')),
    path('api/profile/', UserProfileView.as_view(), name='user-profile'),
    path('api/stats/', UserStatsView.as_view(), name='user-stats'),
    path('', include('apps.users.urls')),
    path('', include('apps.users.activity_urls')),
    path('auth/', include('rest_framework.urls')),

    # ── Serve React built assets (JS, CSS, images) ──
    re_path(r'^assets/(?P<path>.*)$', serve_react_asset, name='react-assets'),

    # ── Serve root-level static files from dist (favicon, manifest, etc.) ──
    re_path(r'^favicon\.svg$', serve_root_static, name='favicon-svg'),
    re_path(r'^favicon\.ico$', serve_root_static, name='favicon-ico'),
    re_path(r'^favicon-96x96\.png$', serve_root_static, name='favicon-png'),
    re_path(r'^apple-touch-icon\.png$', serve_root_static, name='apple-touch-icon'),
    re_path(r'^site\.webmanifest$', serve_root_static, name='site-webmanifest'),

    # ── Django media files ──
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ── React SPA catch-all: must be LAST ──
urlpatterns += [
    re_path(r'^(?!api/|admin/|auth/|static/|media/).*$', serve_react, name='react-spa'),
]

# Error handlers
handler404 = nexus_404
handler500 = nexus_500
