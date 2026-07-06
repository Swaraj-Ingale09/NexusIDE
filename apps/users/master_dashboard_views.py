"""
Advanced Master Admin Dashboard - Comprehensive Platform Analytics and Management
Real-time metrics, user management, API monitoring, and system health
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.db.models import Count, Q, Avg, Sum, F, Max, Min, DurationField, ExpressionWrapper
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from datetime import timedelta
import json

from apps.users.models import UserSession, UserActivity, UserHeartbeat, UserProfile, AdminLog, UserSatisfaction
from apps.compiler.models import AIQuery, ExecutionHistory, CodeSnippet
from apps.compiler.cache_utils import SafeCache
from apps.problems.models import ProblemSubmission, Problem
from apps.projects.models import Project, ProjectFile
from apps.community.models import CommunityPost


class MasterDashboardMetricsView(APIView):
    """Get comprehensive real-time metrics for the master dashboard"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.conf import settings as dj_settings
        if request.user.username != dj_settings.MASTER_ADMIN_USERNAME:
            return Response(
                {'error': 'Unauthorized access'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        cache_key = 'master:dashboard:metrics'
        cached = SafeCache.get(cache_key)
        if cached:
            cached['_cached'] = True
            return Response(cached)
        
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # ===== SYSTEM OVERVIEW =====
        total_users = User.objects.count()
        active_users_today = UserHeartbeat.objects.filter(
            timestamp__gte=today_start, is_active=True
        ).values('user').distinct().count()
        active_users_week = UserHeartbeat.objects.filter(
            timestamp__gte=week_ago, is_active=True
        ).values('user').distinct().count()
        
        # ===== SESSION METRICS =====
        current_sessions = UserSession.objects.filter(logout_time__isnull=True).count()
        total_sessions_today = UserSession.objects.filter(login_time__gte=today_start).count()
        
        closed_sessions = UserSession.objects.filter(
            login_time__gte=month_ago, logout_time__isnull=False
        ).annotate(
            duration=ExpressionWrapper(
                F('logout_time') - F('login_time'),
                output_field=DurationField()
            )
        )
        avg_duration = closed_sessions.aggregate(avg_duration=Avg('duration'))['avg_duration']
        avg_seconds = int(avg_duration.total_seconds()) if avg_duration else 0
        
        # ===== USER ACTIVITY =====
        total_activities_today = UserActivity.objects.filter(timestamp__gte=today_start).count()
        total_activities_week = UserActivity.objects.filter(timestamp__gte=week_ago).count()
        
        activity_breakdown = UserActivity.objects.filter(
            timestamp__gte=month_ago
        ).values('activity_type').annotate(count=Count('id')).order_by('-count')
        
        # ===== CODE EXECUTION =====
        executions_qs = ExecutionHistory.objects.filter(created_at__gte=month_ago)
        executions_count = executions_qs.count()
        successful_executions = executions_qs.filter(status='success').count()
        failed_executions = executions_qs.filter(status='error').count()
        exec_success_rate = (successful_executions / executions_count * 100) if executions_count > 0 else 0
        
        exec_agg = executions_qs.aggregate(
            avg_time=Avg('execution_time'),
            total_time=Sum('execution_time')
        )
        avg_execution_time = exec_agg['avg_time'] or 0
        total_execution_time = exec_agg['total_time'] or 0
        
        # ===== AI USAGE =====
        ai_queries_qs = AIQuery.objects.filter(created_at__gte=month_ago)
        total_ai_queries = ai_queries_qs.count()
        successful_ai = ai_queries_qs.filter(status='success').count()
        failed_ai = ai_queries_qs.filter(status='failed').count()
        ai_success_rate = (successful_ai / total_ai_queries * 100) if total_ai_queries > 0 else 0
        
        ai_agg = ai_queries_qs.aggregate(
            total_tokens=Sum('tokens_used'),
            avg_time=Avg('execution_time')
        )
        total_tokens_used = ai_agg['total_tokens'] or 0
        avg_response_time = ai_agg['avg_time'] or 0
        
        ai_by_provider = list(ai_queries_qs.values('provider').annotate(
            count=Count('id'), tokens=Sum('tokens_used')
        ).order_by('-count'))
        
        ai_by_action = list(ai_queries_qs.values('action').annotate(
            count=Count('id'), tokens=Sum('tokens_used')
        ).order_by('-count'))
        
        # ===== PROBLEM SUBMISSIONS =====
        submissions_qs = ProblemSubmission.objects.filter(submitted_at__gte=month_ago)
        total_submissions = submissions_qs.count()
        accepted_submissions = submissions_qs.filter(status='accepted').count()
        submission_success_rate = (accepted_submissions / total_submissions * 100) if total_submissions > 0 else 0
        
        # ===== CODE SNIPPETS =====
        snippets_qs = CodeSnippet.objects.filter(created_at__gte=month_ago)
        total_snippets = snippets_qs.count()
        public_snippets = snippets_qs.filter(is_public=True).count()
        language_stats = list(snippets_qs.values('language').annotate(count=Count('id')).order_by('-count')[:5])
        
        # ===== PROJECTS =====
        projects_qs = Project.objects.filter(created_at__gte=month_ago)
        total_projects = projects_qs.count()
        project_types = list(projects_qs.values('project_type').annotate(count=Count('id')))
        
        # ===== COMMUNITY =====
        posts_qs = CommunityPost.objects.filter(created_at__gte=month_ago)
        total_posts = posts_qs.count()
        post_categories = list(posts_qs.values('category').annotate(count=Count('id')))
        
        # ===== HOURLY ACTIVITY (all 24 hours, zero-filled) =====
        heartbeats_by_hour_raw = UserHeartbeat.objects.filter(
            timestamp__gte=today_start, is_active=True
        ).annotate(hour=ExtractHour('timestamp')).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        hour_map = {row['hour']: row['count'] for row in heartbeats_by_hour_raw}
        hourly_activity = [
            {'hour': h, 'count': hour_map.get(h, 0)} for h in range(24)
        ]
        
        # ===== DAILY ACTIVITY (last 7 days, zero-filled) =====
        last_7_days = [today_start - timedelta(days=i) for i in reversed(range(7))]
        activity_by_day_qs = UserActivity.objects.filter(
            timestamp__date__gte=last_7_days[0].date()
        ).annotate(day=TruncDate('timestamp')).values('day').annotate(count=Count('id'))
        activity_by_day_map = {row['day'].isoformat(): row['count'] for row in activity_by_day_qs}
        daily_activity = [
            {'date': day.date().isoformat(), 'day': day.strftime('%a'), 'count': activity_by_day_map.get(day.date().isoformat(), 0)}
            for day in last_7_days
        ]
        
        # Daily active users (last 7 days, zero-filled)
        dau_qs = UserHeartbeat.objects.filter(
            timestamp__date__gte=last_7_days[0].date(), is_active=True
        ).annotate(day=TruncDate('timestamp')).values('day').annotate(count=Count('user', distinct=True))
        dau_map = {row['day'].isoformat(): row['count'] for row in dau_qs}
        daily_active_users = [
            {'date': day.date().isoformat(), 'count': dau_map.get(day.date().isoformat(), 0)}
            for day in last_7_days
        ]
        
        # ===== WEEKLY AI TOKENS (last 4 weeks) =====
        weekly_ai_tokens = []
        for idx in range(4):
            w_start = today_start - timedelta(days=28 - idx * 7)
            w_end = w_start + timedelta(days=7)
            tokens = AIQuery.objects.filter(
                created_at__gte=w_start, created_at__lt=w_end
            ).aggregate(total=Sum('tokens_used'))['total'] or 0
            weekly_ai_tokens.append({
                'label': w_start.strftime('%b %d'),
                'tokens': int(tokens)
            })
        
        # ===== LANGUAGE POPULARITY (DB-aggregated, no Python loop) =====
        exec_lang_qs = ExecutionHistory.objects.filter(
            created_at__gte=month_ago
        ).values('metadata__language').annotate(
            exec_count=Count('id')
        ).order_by('-exec_count')
        exec_lang_map = {}
        for row in exec_lang_qs:
            lang = (row.get('metadata__language') or 'unknown').lower()
            exec_lang_map[lang] = row['exec_count']
        
        language_popularity = []
        total_lang_count = sum(item['count'] for item in language_stats) or 1
        for item in language_stats:
            lang = (item['language'] or 'unknown').lower()
            language_popularity.append({
                'language': lang,
                'count': item['count'],
                'executions': exec_lang_map.get(lang, 0),
                'percentage': round((item['count'] / total_lang_count) * 100, 1)
            })
        
        # ===== AI ACTION BREAKDOWN =====
        ai_action_breakdown = []
        for action_item in ai_queries_qs.values('action').annotate(
            count=Count('id'),
            success=Count('id', filter=Q(status='success')),
            avg_time=Avg('execution_time')
        ).order_by('-count'):
            total = action_item['count']
            ai_action_breakdown.append({
                'action': action_item['action'] or 'unknown',
                'count': total,
                'success_rate': round((action_item['success'] / total * 100) if total > 0 else 0, 1),
                'avg_time': round(action_item['avg_time'] or 0, 3)
            })
        
        # ===== SATISFACTION =====
        satisfaction_qs = UserSatisfaction.objects.filter(submitted_at__gte=month_ago)
        satisfaction_count = satisfaction_qs.count()
        avg_satisfaction = satisfaction_qs.aggregate(Avg('rating'))['rating__avg'] or 0
        recommended_count = satisfaction_qs.filter(would_recommend=True).count()
        recommended_percent = (recommended_count / satisfaction_count * 100) if satisfaction_count > 0 else 0
        
        api_usage = {
            'ai_queries': total_ai_queries,
            'code_executions': executions_count,
            'problem_submissions': total_submissions,
            'activity_logs': total_activities_today,
        }
        api_usage['total'] = sum(api_usage.values())
        
        # ===== TOP PERFORMERS (with AI + streak data) =====
        top_user_ids = User.objects.annotate(
            activity_count=Count('activities'),
        ).order_by('-activity_count')[:10].values_list('id', flat=True)
        
        top_exec_map = {
            row['user_id']: row
            for row in ExecutionHistory.objects.filter(user_id__in=top_user_ids).values('user_id').annotate(
                exec_count=Count('id'),
                total_exec_time=Sum('execution_time')
            )
        }
        top_ai_map = {
            row['user_id']: row
            for row in AIQuery.objects.filter(user_id__in=top_user_ids).values('user_id').annotate(
                ai_count=Count('id'),
                ai_tokens=Sum('tokens_used')
            )
        }
        
        top_users_data = []
        for user in User.objects.filter(id__in=top_user_ids).select_related('profile'):
            profile = getattr(user, 'profile', None)
            exec_info = top_exec_map.get(user.id, {})
            ai_info = top_ai_map.get(user.id, {})
            top_users_data.append({
                'id': user.id,
                'username': user.username,
                'xp': profile.xp_points if profile else 0,
                'level': profile.level if profile else 1,
                'executions': exec_info.get('exec_count', 0),
                'total_exec_time': round(exec_info.get('total_exec_time') or 0, 1),
                'ai_queries': ai_info.get('ai_count', 0),
                'ai_tokens': ai_info.get('ai_tokens', 0),
                'streak': profile.streak_days if profile else 0,
                'code_quality': round(profile.code_quality_score, 1) if profile else 0,
            })
        top_users_data.sort(key=lambda x: x['xp'] + x['executions'] * 10 + x['ai_queries'] * 5, reverse=True)
        top_users_data = top_users_data[:8]
        
        response_data = {
            'timestamp': now.isoformat(),
            'overview': {
                'total_users': total_users,
                'active_today': active_users_today,
                'active_week': active_users_week,
                'current_sessions': current_sessions,
                'sessions_today': total_sessions_today,
                'avg_session_duration_seconds': avg_seconds,
            },
            'activity': {
                'total_today': total_activities_today,
                'total_week': total_activities_week,
                'breakdown': [
                    {'type': a['activity_type'], 'count': a['count']}
                    for a in activity_breakdown
                ]
            },
            'code_execution': {
                'total': executions_count,
                'successful': successful_executions,
                'failed': failed_executions,
                'success_rate': round(exec_success_rate, 2),
                'avg_execution_time': round(avg_execution_time, 3),
                'total_execution_time': int(total_execution_time),
            },
            'ai_usage': {
                'total_queries': total_ai_queries,
                'successful': successful_ai,
                'failed': failed_ai,
                'success_rate': round(ai_success_rate, 2),
                'total_tokens': total_tokens_used,
                'avg_response_time': round(avg_response_time, 3),
                'by_provider': [
                    {'provider': p['provider'], 'count': p['count'], 'tokens': p['tokens']}
                    for p in ai_by_provider
                ],
                'by_action': [
                    {'action': a['action'], 'count': a['count'], 'tokens': a['tokens']}
                    for a in ai_by_action
                ]
            },
            'problems': {
                'total_submissions': total_submissions,
                'accepted': accepted_submissions,
                'success_rate': round(submission_success_rate, 2),
            },
            'snippets': {
                'total': total_snippets,
                'public': public_snippets,
                'private': total_snippets - public_snippets,
                'languages': [
                    {'language': l['language'], 'count': l['count']}
                    for l in language_stats
                ]
            },
            'projects': {
                'total': total_projects,
                'by_type': [
                    {'type': p['project_type'], 'count': p['count']}
                    for p in project_types
                ]
            },
            'community': {
                'total_posts': total_posts,
                'by_category': [
                    {'category': c['category'], 'count': c['count']}
                    for c in post_categories
                ]
            },
            'hourly_activity': hourly_activity,
            'daily_activity': daily_activity,
            'daily_active_users': daily_active_users,
            'weekly_ai_tokens': weekly_ai_tokens,
            'language_popularity': language_popularity,
            'ai_action_breakdown': ai_action_breakdown,
            'satisfaction': {
                'average_rating': round(avg_satisfaction, 2),
                'feedback_count': satisfaction_count,
                'recommended_percent': round(recommended_percent, 2)
            },
            'api_usage': api_usage,
            'top_performers': top_users_data,
        }
        
        SafeCache.set(cache_key, response_data, 120)
        
        AdminLog.objects.create(
            admin_user=request.user,
            action="Accessed master dashboard metrics"
        )
        
        return Response(response_data)


class MasterDashboardUsersView(APIView):
    """Detailed user management for master dashboard with comprehensive analytics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.conf import settings as dj_settings
        if request.user.username != dj_settings.MASTER_ADMIN_USERNAME:
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Pagination
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            offset = (page - 1) * page_size
            
            # Search and filter
            search = request.query_params.get('search', '')
            sort_by = request.query_params.get('sort_by', '-date_joined')
            filter_active = request.query_params.get('active_only', 'false') == 'true'
            
            users_query = User.objects.all()
            
            if search:
                users_query = users_query.filter(
                    Q(username__icontains=search) | Q(email__icontains=search)
                )
            
            if filter_active:
                # Filter for active users (with sessions in last 7 days)
                week_ago = timezone.now() - timedelta(days=7)
                active_user_ids = UserSession.objects.filter(
                    login_time__gte=week_ago
                ).values_list('user_id', flat=True).distinct()
                users_query = users_query.filter(id__in=active_user_ids)
            
            total_count = users_query.count()
            users = users_query.select_related('profile').order_by(sort_by)[offset:offset + page_size]
            user_ids = [u.id for u in users]

            session_map = {}
            if user_ids:
                all_sessions = UserSession.objects.filter(user_id__in=user_ids).values('user_id').annotate(
                    total_sessions=Count('id'),
                    last_login=Max('login_time')
                )
                session_map = {row['user_id']: row for row in all_sessions}

            closed_session_map = {}
            if user_ids:
                closed_sessions = UserSession.objects.filter(
                    user_id__in=user_ids,
                    logout_time__isnull=False
                ).annotate(
                    duration=ExpressionWrapper(
                        F('logout_time') - F('login_time'),
                        output_field=DurationField()
                    )
                ).values('user_id').annotate(
                    total_closed_sessions=Count('id'),
                    total_duration=Sum('duration')
                )
                closed_session_map = {row['user_id']: row for row in closed_sessions}

            recent_sessions_map = {
                row['user_id']: row['recent_sessions']
                for row in UserSession.objects.filter(
                    user_id__in=user_ids,
                    login_time__gte=timezone.now() - timedelta(days=7)
                ).values('user_id').annotate(recent_sessions=Count('id'))
            }

            activity_map = {
                row['user_id']: row['count']
                for row in UserActivity.objects.filter(user_id__in=user_ids).values('user_id').annotate(count=Count('id'))
            }

            execution_map = {
                row['user_id']: row
                for row in ExecutionHistory.objects.filter(user_id__in=user_ids).values('user_id').annotate(
                    total_code_executions=Count('id'),
                    successful_executions=Count('id', filter=Q(status='success')),
                    failed_executions=Count('id', filter=Q(status='error')),
                    total_execution_time=Sum('execution_time'),
                    avg_execution_time=Avg('execution_time')
                )
            }

            ai_map = {
                row['user_id']: row
                for row in AIQuery.objects.filter(user_id__in=user_ids).values('user_id').annotate(
                    total_ai_tokens=Sum('tokens_used'),
                    total_ai_queries=Count('id'),
                    successful_ai=Count('id', filter=Q(status='success')),
                    avg_tokens=Avg('tokens_used')
                )
            }

            snippet_map = {
                row['user_id']: row['count']
                for row in CodeSnippet.objects.filter(user_id__in=user_ids).values('user_id').annotate(count=Count('id'))
            }

            satisfaction_map = {
                row['user_id']: row
                for row in UserSatisfaction.objects.filter(user_id__in=user_ids).values('user_id').annotate(
                    avg_rating=Avg('rating'),
                    count=Count('id')
                )
            }

            submission_map = {
                row['user_id']: row
                for row in ProblemSubmission.objects.filter(user_id__in=user_ids).values('user_id').annotate(
                    total_submissions=Count('id'),
                    accepted_submissions=Count('id', filter=Q(status='accepted'))
                )
            }

            active_heartbeat_map = {
                row['user_id']: row['count']
                for row in UserHeartbeat.objects.filter(user_id__in=user_ids, is_active=True).values('user_id').annotate(count=Count('id'))
            }

            users_data = []
            for user in users:
                profile = getattr(user, 'profile', None)
                session_info = session_map.get(user.id, {})
                closed_session_info = closed_session_map.get(user.id, {})
                exec_info = execution_map.get(user.id, {})
                ai_info = ai_map.get(user.id, {})
                submission_info = submission_map.get(user.id, {})
                snippet_count = snippet_map.get(user.id, 0) or (profile.total_snippets_created if profile else 0)
                satisfaction_info = satisfaction_map.get(user.id, {})

                total_session_time = closed_session_info.get('total_duration')
                total_session_seconds = int(total_session_time.total_seconds()) if total_session_time else (profile.total_session_time if profile else 0)
                closed_sessions_count = closed_session_info.get('total_closed_sessions', 0)
                avg_session_seconds = int(total_session_seconds / closed_sessions_count) if closed_sessions_count > 0 else 0

                total_code_executions = exec_info.get('total_code_executions') or (profile.total_code_executions if profile else 0)
                total_ai_tokens = ai_info.get('total_ai_tokens') or (profile.total_ai_tokens_used if profile else 0)
                total_activities = activity_map.get(user.id, 0)
                total_sessions = session_info.get('total_sessions', 0)
                total_logins = total_sessions
                logins_last_week = recent_sessions_map.get(user.id, 0)
                real_time_spent_minutes = active_heartbeat_map.get(user.id, 0)
                last_login = session_info.get('last_login')

                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'date_joined': user.date_joined.isoformat(),
                    'last_login': last_login.isoformat() if last_login else None,

                    'xp_points': profile.xp_points if profile else 0,
                    'level': profile.level if profile else 1,
                    'streak_days': profile.streak_days if profile else 0,
                    'code_quality_score': round(profile.code_quality_score, 2) if profile else 0,
                    'favorite_language': profile.favorite_language if profile else 'unknown',

                    'total_logins': total_logins,
                    'logins_last_week': logins_last_week,
                    'total_sessions': total_sessions,
                    'total_session_time_seconds': total_session_seconds,
                    'avg_session_time_seconds': avg_session_seconds,
                    'real_time_spent_minutes': real_time_spent_minutes,

                    'total_code_executions': total_code_executions,
                    'successful_executions': exec_info.get('successful_executions', 0),
                    'failed_executions': exec_info.get('failed_executions', 0),
                    'execution_success_rate': round((exec_info.get('successful_executions', 0) / total_code_executions * 100), 2) if total_code_executions > 0 else 0,
                    'total_execution_time': round(exec_info.get('total_execution_time') or 0, 2),
                    'avg_execution_time': round(exec_info.get('avg_execution_time') or 0, 3),

                    'total_ai_queries': ai_info.get('total_ai_queries', 0),
                    'total_ai_tokens': total_ai_tokens,
                    'avg_tokens_per_query': round(ai_info.get('avg_tokens') or 0, 1),
                    'ai_success_rate': round((ai_info.get('successful_ai', 0) / ai_info.get('total_ai_queries', 1) * 100), 2) if ai_info.get('total_ai_queries', 0) > 0 else 0,

                    'total_submissions': submission_info.get('total_submissions', 0),
                    'accepted_submissions': submission_info.get('accepted_submissions', 0),
                    'submission_success_rate': round((submission_info.get('accepted_submissions', 0) / submission_info.get('total_submissions', 1) * 100), 2) if submission_info.get('total_submissions', 0) > 0 else 0,
                    'total_snippets': snippet_count,
                    'satisfaction_rating': round(satisfaction_info.get('avg_rating') or 0, 2) if satisfaction_info.get('count') else None,

                    'total_activities': total_activities,
                    'recent_activities': [],
                })

            total_pages = (total_count + page_size - 1) // page_size
            
            AdminLog.objects.create(
                admin_user=request.user,
                action=f"Viewed users list (page {page}, search: {search})"
            )
            
            return Response({
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': total_pages,
                'users': users_data
            })
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("MasterDashboardUsersView error")
            return Response({
                'error': 'Failed to load user data',
                'count': 0,
                'page': 1,
                'page_size': 10,
                'total_pages': 0,
                'users': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MasterDashboardAPIMonitorView(APIView):
    """Monitor API usage and performance"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.conf import settings as dj_settings
        if request.user.username != dj_settings.MASTER_ADMIN_USERNAME:
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        now = timezone.now()
        period_days = int(request.query_params.get('days', 7))
        period_start = now - timedelta(days=period_days)
        
        # API Calls by type
        ai_api_calls = AIQuery.objects.filter(created_at__gte=period_start)
        execution_calls = ExecutionHistory.objects.filter(created_at__gte=period_start)
        submission_calls = ProblemSubmission.objects.filter(submitted_at__gte=period_start)
        
        # Response times
        ai_avg_response = ai_api_calls.aggregate(Avg('execution_time'))['execution_time__avg'] or 0
        exec_avg_response = execution_calls.aggregate(Avg('execution_time'))['execution_time__avg'] or 0
        
        # Error rates
        ai_error_rate = (ai_api_calls.filter(status='failed').count() / ai_api_calls.count() * 100) if ai_api_calls.count() > 0 else 0
        exec_error_rate = (execution_calls.filter(status='error').count() / execution_calls.count() * 100) if execution_calls.count() > 0 else 0
        
        # API calls by provider
        provider_stats = ai_api_calls.values('provider').annotate(
            count=Count('id'),
            avg_time=Avg('execution_time'),
            errors=Count('id', filter=Q(status='failed'))
        )
        
        AdminLog.objects.create(
            admin_user=request.user,
            action="Viewed API monitor"
        )
        
        return Response({
            'period_days': period_days,
            'api_stats': {
                'ai_queries': {
                    'total': ai_api_calls.count(),
                    'avg_response_time': round(ai_avg_response, 3),
                    'error_rate': round(ai_error_rate, 2),
                    'by_provider': [
                        {
                            'provider': p['provider'],
                            'count': p['count'],
                            'avg_response_time': round(p['avg_time'], 3),
                            'errors': p['errors']
                        }
                        for p in provider_stats
                    ]
                },
                'code_executions': {
                    'total': execution_calls.count(),
                    'avg_response_time': round(exec_avg_response, 3),
                    'error_rate': round(exec_error_rate, 2),
                },
                'problem_submissions': {
                    'total': submission_calls.count(),
                }
            }
        })


class MasterDashboardSystemHealthView(APIView):
    """System health and performance metrics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from django.conf import settings as dj_settings
        if request.user.username != dj_settings.MASTER_ADMIN_USERNAME:
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        now = timezone.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        # Database stats
        user_count = User.objects.count()
        session_count = UserSession.objects.count()
        activity_count = UserActivity.objects.count()
        ai_query_count = AIQuery.objects.count()
        execution_count = ExecutionHistory.objects.count()
        
        # Recent errors
        recent_errors = ExecutionHistory.objects.filter(
            created_at__gte=hour_ago,
            status='error'
        ).count()
        
        # Active sessions
        active_sessions = UserSession.objects.filter(logout_time__isnull=True).count()
        
        # System load indicators
        activities_last_hour = UserActivity.objects.filter(timestamp__gte=hour_ago).count()
        activities_last_day = UserActivity.objects.filter(timestamp__gte=day_ago).count()
        
        AdminLog.objects.create(
            admin_user=request.user,
            action="Viewed system health"
        )
        
        return Response({
            'database': {
                'users': user_count,
                'sessions': session_count,
                'activities': activity_count,
                'ai_queries': ai_query_count,
                'executions': execution_count,
            },
            'current_state': {
                'active_sessions': active_sessions,
                'recent_errors_1h': recent_errors,
                'activities_last_hour': activities_last_hour,
                'activities_last_24h': activities_last_day,
            },
            'health_status': 'healthy' if recent_errors < 100 and active_sessions < 1000 else 'warning'
        })


class MasterDashboardUserDetailView(APIView):
    """Detailed analytics for a specific user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        from django.conf import settings as dj_settings
        if request.user.username != dj_settings.MASTER_ADMIN_USERNAME:
            return Response(
                {'error': 'Unauthorized'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        profile = user.profile
        
        # Time ranges
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Sessions
        all_sessions = UserSession.objects.filter(user=user)
        recent_sessions = all_sessions.filter(login_time__gte=week_ago)
        
        session_agg = all_sessions.filter(logout_time__isnull=False).annotate(
            duration=ExpressionWrapper(
                F('logout_time') - F('login_time'),
                output_field=DurationField()
            )
        ).aggregate(
            total_duration=Sum('duration'),
            avg_duration=Avg('duration')
        )
        total_session_seconds = int(session_agg['total_duration'].total_seconds()) if session_agg['total_duration'] else 0
        avg_session_seconds = int(session_agg['avg_duration'].total_seconds()) if session_agg['avg_duration'] else 0
        
        # Login history
        login_history = []
        for session in recent_sessions.order_by('-login_time')[:10]:
            login_history.append({
                'login_time': session.login_time.isoformat(),
                'logout_time': session.logout_time.isoformat() if session.logout_time else None,
                'duration_seconds': int(session.get_session_duration()),
                'ip_address': session.ip_address,
            })
        
        # Code executions - detailed
        executions = ExecutionHistory.objects.filter(user=user)
        recent_executions = executions.filter(created_at__gte=week_ago)
        
        exec_timeline = []
        for exec_hist in recent_executions.order_by('-created_at')[:20]:
            exec_timeline.append({
                'timestamp': exec_hist.created_at.isoformat(),
                'language': exec_hist.language,
                'status': exec_hist.status,
                'execution_time': exec_hist.execution_time,
                'memory_used': exec_hist.memory_used,
            })
        
        # AI queries - detailed
        ai_queries = AIQuery.objects.filter(user=user)
        recent_ai = ai_queries.filter(created_at__gte=week_ago)
        
        ai_timeline = []
        for query in recent_ai.order_by('-created_at')[:20]:
            ai_timeline.append({
                'timestamp': query.created_at.isoformat(),
                'action': query.action,
                'provider': query.provider,
                'status': query.status,
                'tokens_used': query.tokens_used,
                'execution_time': query.execution_time,
            })
        
        # Problem submissions - detailed
        submissions = ProblemSubmission.objects.filter(user=user)
        recent_submissions = submissions.filter(submitted_at__gte=week_ago)
        
        submission_timeline = []
        for sub in recent_submissions.order_by('-submitted_at')[:20]:
            submission_timeline.append({
                'timestamp': sub.submitted_at.isoformat(),
                'problem': sub.problem.title if sub.problem else 'Unknown',
                'status': sub.status,
                'language': sub.language,
                'execution_time': sub.execution_time,
                'passed_tests': f"{sub.passed_tests}/{sub.total_tests}",
            })
        
        # Daily activity breakdown
        daily_activity = {}
        activities = UserActivity.objects.filter(user=user, timestamp__gte=week_ago)
        for activity in activities:
            date_key = activity.timestamp.date().isoformat()
            if date_key not in daily_activity:
                daily_activity[date_key] = {}
            activity_type = activity.activity_type
            daily_activity[date_key][activity_type] = daily_activity[date_key].get(activity_type, 0) + 1
        
        # Hourly activity (today)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hourly_activity = {}
        today_activities = UserActivity.objects.filter(user=user, timestamp__gte=today_start)
        for activity in today_activities:
            hour = activity.timestamp.hour
            hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
        
        # Calculate metrics
        total_exec_time = executions.aggregate(Sum('execution_time'))['execution_time__sum'] or 0
        avg_exec_time = executions.aggregate(Avg('execution_time'))['execution_time__avg'] or 0
        max_exec_time = executions.aggregate(Max('execution_time'))['execution_time__max'] or 0
        
        # Streak and consistency
        last_activity = activities.order_by('-timestamp').first()
        last_activity_date = last_activity.timestamp.date() if last_activity else None
        
        AdminLog.objects.create(
            admin_user=request.user,
            action=f"Viewed detailed profile for user: {user.username}"
        )
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            },
            'profile': {
                'xp_points': profile.xp_points if profile else 0,
                'level': profile.level if profile else 1,
                'streak_days': profile.streak_days if profile else 0,
                'code_quality_score': round(profile.code_quality_score, 2) if profile else 0,
                'favorite_language': profile.favorite_language if profile else 'unknown',
                'last_activity_date': last_activity_date.isoformat() if last_activity_date else None,
            },
            'session_stats': {
                'total_logins': all_sessions.count(),
                'logins_this_week': recent_sessions.count(),
                'total_session_time': total_session_seconds,
                'avg_session_duration': avg_session_seconds,
                'login_history': login_history,
            },
            'execution_stats': {
                'total_executions': executions.count(),
                'executions_this_week': recent_executions.count(),
                'successful': executions.filter(status='success').count(),
                'failed': executions.filter(status='error').count(),
                'success_rate': round((executions.filter(status='success').count() / executions.count() * 100) if executions.count() > 0 else 0, 2),
                'total_execution_time': round(total_exec_time, 2),
                'avg_execution_time': round(avg_exec_time, 3),
                'max_execution_time': round(max_exec_time, 3),
                'recent_executions': exec_timeline,
            },
            'ai_stats': {
                'total_queries': ai_queries.count(),
                'queries_this_week': recent_ai.count(),
                'total_tokens': ai_queries.aggregate(Sum('tokens_used'))['tokens_used__sum'] or 0,
                'avg_tokens_per_query': round((ai_queries.aggregate(Avg('tokens_used'))['tokens_used__avg'] or 0), 1),
                'success_rate': round((ai_queries.filter(status='success').count() / ai_queries.count() * 100) if ai_queries.count() > 0 else 0, 2),
                'recent_queries': ai_timeline,
                'by_provider': [
                    {'provider': p['provider'], 'count': p['count']}
                    for p in ai_queries.values('provider').annotate(count=Count('id')).order_by('-count')
                ],
                'by_action': [
                    {'action': a['action'], 'count': a['count']}
                    for a in ai_queries.values('action').annotate(count=Count('id')).order_by('-count')
                ],
            },
            'problem_stats': {
                'total_submissions': submissions.count(),
                'submissions_this_week': recent_submissions.count(),
                'accepted': submissions.filter(status='accepted').count(),
                'success_rate': round((submissions.filter(status='accepted').count() / submissions.count() * 100) if submissions.count() > 0 else 0, 2),
                'recent_submissions': submission_timeline,
            },
            'activity_patterns': {
                'daily': daily_activity,
                'hourly_today': hourly_activity,
                'total_activities': activities.count(),
            }
        })
