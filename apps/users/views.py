import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, logout
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
from apps.users.models import (
    UserProfile, Achievement, UserSession, UserActivity,
    UserSatisfaction, AdminLog, PasswordResetToken, EmailVerificationToken, UserHeartbeat
)
from apps.users.serializers import (
    UserSerializer, UserProfileSerializer, AchievementSerializer,
    UserRegistrationSerializer, UserLoginSerializer, UserSessionSerializer,
    UserActivitySerializer, UserSatisfactionSerializer
)
from apps.compiler.cache_utils import SafeCache

logger = logging.getLogger(__name__)


def _safe_int(value, default=1, min_val=1, max_val=1000):
    """Safely convert value to int with bounds."""
    try:
        result = int(value)
        return max(min_val, min(max_val, result))
    except (TypeError, ValueError):
        return default


def _admin_check(user):
    """Check if user has admin privileges."""
    return user.is_staff or user.is_superuser


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'success': True,
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        except Exception:
            logger.exception("Registration failed")
            return Response({
                'success': False,
                'error': 'Registration failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def login(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        ip_address = self.get_client_ip(request)

        # Check brute force protection
        from config.rate_limiter import BruteForceProtection
        if BruteForceProtection.is_locked(username):
            remaining = BruteForceProtection.get_lockout_time_remaining(username)
            return Response({
                'success': False,
                'error': f'Account temporarily locked due to too many failed attempts. Try again in {remaining} seconds.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        user = authenticate(
            username=username,
            password=serializer.validated_data['password']
        )
        if not user:
            # Record failed attempt
            BruteForceProtection.record_failed_login(username)
            return Response({
                'success': False,
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)

        try:
            ip_address = self.get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            UserSession.objects.create(
                user=user, ip_address=ip_address, user_agent=user_agent
            )

            # Clear failed login attempts on successful login
            BruteForceProtection.record_successful_login(username)

            if _admin_check(user):
                AdminLog.objects.create(
                    admin_user=user,
                    action=f"Admin logged in from {ip_address}"
                )

            from django.conf import settings as dj_settings
            user_data = UserSerializer(user).data
            user_data['is_staff'] = user.is_staff
            user_data['is_superuser'] = user.is_superuser
            user_data['is_master_admin'] = (
                user.username == dj_settings.MASTER_ADMIN_USERNAME
            )

            refresh = RefreshToken.for_user(user)
            return Response({
                'success': True,
                'user': user_data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Login processing failed for user %s", user.username)
            return Response({
                'success': False,
                'error': 'Login failed. Please try again.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        if request.user.is_authenticated:
            try:
                last_session = UserSession.objects.filter(
                    user=request.user, logout_time__isnull=True
                ).last()
                if last_session:
                    last_session.logout_time = timezone.now()
                    last_session.save(update_fields=['logout_time'])
            except Exception:
                logger.exception("Failed to close session for user %s", request.user.username)

        return Response({
            'success': True,
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)

        serializer = UserProfileSerializer(profile)
        data = serializer.data

        from django.conf import settings as dj_settings
        data['is_staff'] = request.user.is_staff
        data['is_superuser'] = request.user.is_superuser
        data['is_master_admin'] = (
            request.user.username == dj_settings.MASTER_ADMIN_USERNAME
        )
        return Response(data)

    def put(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.create(user=request.user)

        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            data = serializer.data

            from django.conf import settings as dj_settings
            data['is_staff'] = request.user.is_staff
            data['is_superuser'] = request.user.is_superuser
            data['is_master_admin'] = (
                request.user.username == dj_settings.MASTER_ADMIN_USERNAME
            )
            return Response(data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminDashboardView(APIView):
    """Admin-only dashboard with real analytics."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _admin_check(request.user):
            return Response(
                {'error': 'Access denied. Admin privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )

        from apps.users.analytics import RealisticAnalytics

        cache_key = 'admin:dashboard'
        cached_data = SafeCache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        AdminLog.objects.create(
            admin_user=request.user,
            action="Accessed admin dashboard"
        )

        response_data = RealisticAnalytics.get_realistic_dashboard_data(days=30)
        SafeCache.set(cache_key, response_data, 300)
        return Response(response_data)


class AdminUsersDetailView(APIView):
    """Get detailed information about all users with pagination."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _admin_check(request.user):
            return Response(
                {'error': 'Access denied. Admin privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )

        from apps.compiler.models import ExecutionHistory, CodeSnippet, AIQuery

        page = _safe_int(request.query_params.get('page', 1))
        page_size = _safe_int(request.query_params.get('page_size', 20), max_val=100)
        offset = (page - 1) * page_size

        total_users = User.objects.count()

        users = User.objects.select_related('profile').prefetch_related(
            'sessions', 'activities'
        ).order_by('-date_joined')[offset:offset + page_size]

        users_data = []
        for user in users:
            sessions = user.sessions.all()
            total_time = sum(
                (s.get_session_duration() for s in sessions if s.logout_time),
                0
            )

            activities_count = SafeCache.get_or_set(
                f'admin:user:{user.id}:activities',
                lambda u=user: UserActivity.objects.filter(user=u).count(),
                300
            )

            satisfaction = user.satisfaction_ratings.order_by('-submitted_at').first()

            user_ai_tokens = SafeCache.get_or_set(
                f'admin:user:{user.id}:tokens',
                lambda u=user: AIQuery.objects.filter(user=u).aggregate(
                    Sum('tokens_used')
                )['tokens_used__sum'] or 0,
                3600
            )

            user_executions = ExecutionHistory.objects.filter(user=user).count()
            user_snippets = CodeSnippet.objects.filter(user=user).count()
            code_quality = getattr(user.profile, 'code_quality_score', 0)

            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined,
                'total_sessions': sessions.count(),
                'total_time_spent': f"{int(total_time // 3600)}h {int((total_time % 3600) // 60)}m",
                'last_login': user.last_login,
                'activities_count': activities_count,
                'satisfaction_rating': satisfaction.rating if satisfaction else None,
                'would_recommend': satisfaction.would_recommend if satisfaction else None,
                'ai_tokens_used': user_ai_tokens,
                'code_executions': user_executions,
                'snippets_created': user_snippets,
                'code_quality_score': round(code_quality, 2)
            })

        total_pages = (total_users + page_size - 1) // page_size

        return Response({
            'count': total_users,
            'next': f'/api/admin/users/?page={page + 1}' if page < total_pages else None,
            'previous': f'/api/admin/users/?page={page - 1}' if page > 1 else None,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'results': users_data
        })


class AdminUserDetailView(APIView):
    """Get detailed information about a specific user."""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        if not _admin_check(request.user):
            return Response(
                {'error': 'Access denied. Admin privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = User.objects.select_related('profile').get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        sessions = UserSession.objects.filter(user=user)
        sessions_data = UserSessionSerializer(sessions, many=True).data

        activities = UserActivity.objects.filter(user=user).order_by('-timestamp')[:50]
        activities_data = UserActivitySerializer(activities, many=True).data

        satisfaction = UserSatisfaction.objects.filter(user=user).order_by('-submitted_at').first()
        satisfaction_data = UserSatisfactionSerializer(satisfaction).data if satisfaction else None

        profile_data = UserProfileSerializer(user.profile).data if hasattr(user, 'profile') else {}

        total_time = sum(
            (s.get_session_duration() for s in sessions if s.logout_time),
            0
        )

        return Response({
            'user': UserSerializer(user).data,
            'profile': profile_data,
            'sessions': sessions_data,
            'activities': activities_data,
            'satisfaction': satisfaction_data,
            'statistics': {
                'total_sessions': sessions.count(),
                'total_time_spent': f"{int(total_time // 3600)}h",
                'total_activities': UserActivity.objects.filter(user=user).count(),
                'last_activity': user.last_login
            }
        })


class AdminActivityLogView(APIView):
    """Get all user activities."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _admin_check(request.user):
            return Response(
                {'error': 'Access denied. Admin privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )

        activity_type = request.query_params.get('type')
        limit = _safe_int(request.query_params.get('limit', 100), max_val=500)

        activities = UserActivity.objects.select_related('user').order_by('-timestamp')
        if activity_type:
            activities = activities.filter(activity_type=activity_type)

        return Response(UserActivitySerializer(activities[:limit], many=True).data)


class UserActivityTrackingView(APIView):
    """Track user activities and update statistics."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        activity_type = request.data.get('activity_type')
        description = request.data.get('description', '')

        if not activity_type:
            return Response(
                {'error': 'activity_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_types = [c[0] for c in UserActivity.ACTIVITY_CHOICES]
        if activity_type not in valid_types:
            return Response(
                {'error': f'Invalid activity_type. Valid: {", ".join(valid_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        UserActivity.objects.create(
            user=request.user,
            activity_type=activity_type,
            description=description
        )

        try:
            profile = request.user.profile
            if activity_type == 'compile':
                profile.total_code_executions += 1
                profile.save(update_fields=['total_code_executions'])
            elif activity_type == 'snippet_create':
                profile.total_snippets_created += 1
                profile.save(update_fields=['total_snippets_created'])
        except Exception:
            logger.debug("Could not update profile stats for %s", request.user.username)

        return Response({'success': True}, status=status.HTTP_201_CREATED)


class UserSatisfactionView(APIView):
    """Submit satisfaction feedback."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = UserSatisfactionSerializer(data=request.data)
        if serializer.is_valid():
            satisfaction = UserSatisfaction.objects.create(
                user=request.user,
                **serializer.validated_data
            )
            return Response(
                UserSatisfactionSerializer(satisfaction).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        if not _admin_check(request.user):
            satisfaction = UserSatisfaction.objects.filter(user=request.user).order_by('-submitted_at').first()
            if satisfaction:
                return Response(UserSatisfactionSerializer(satisfaction).data)
            return Response(None)

        satisfactions = UserSatisfaction.objects.select_related('user').order_by('-submitted_at')
        return Response(UserSatisfactionSerializer(satisfactions, many=True).data)


@method_decorator(csrf_exempt, name='dispatch')
class MasterAdminVerifyView(APIView):
    """
    Verifies JWT token, checks master admin status, sets server-side session.
    CSRF exempt because frontend sends Bearer token, not CSRF token.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        from django.conf import settings as dj_settings
        from django.http import JsonResponse
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'ok': False, 'error': 'No token provided.'}, status=401)

        token_str = auth_header.split(' ', 1)[1]

        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token_str)
            user = jwt_auth.get_user(validated_token)
        except (InvalidToken, TokenError):
            return JsonResponse({'ok': False, 'error': 'Invalid token.'}, status=401)
        except Exception:
            logger.exception("Token verification failed")
            return JsonResponse({'ok': False, 'error': 'Authentication failed.'}, status=401)

        if user.username != dj_settings.MASTER_ADMIN_USERNAME:
            return JsonResponse({'ok': False, 'error': 'Access denied.'}, status=403)

        if not _admin_check(user):
            return JsonResponse({'ok': False, 'error': 'Access denied.'}, status=403)

        request.session.cycle_key()
        request.session['master_admin_verified'] = True
        request.session['master_admin_user'] = user.username
        request.session.modified = True
        request.session.set_expiry(3600 * 8)
        request.session.save()

        AdminLog.objects.create(admin_user=user, action="Master admin dashboard access")

        return JsonResponse({'ok': True, 'redirect': '/master/dashboard/'})


class MasterAdminDashboardView(TemplateView):
    """Master admin dashboard - requires server-side session flag."""
    template_name = 'admin/master_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        from django.conf import settings as dj_settings
        verified = request.session.get('master_admin_verified')
        correct_user = request.session.get('master_admin_user') == dj_settings.MASTER_ADMIN_USERNAME
        if not verified or not correct_user:
            return HttpResponseRedirect('/')
        return super().dispatch(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class MasterAdminLogoutView(APIView):
    """Clear the server-side admin session flag."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        request.session.pop('master_admin_verified', None)
        request.session.pop('master_admin_user', None)
        from django.http import JsonResponse
        return JsonResponse({'success': True})


class LogoutView(APIView):
    """Custom logout view that redirects to home."""
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            try:
                last_session = UserSession.objects.filter(
                    user=request.user, logout_time__isnull=True
                ).last()
                if last_session:
                    last_session.logout_time = timezone.now()
                    last_session.save(update_fields=['logout_time'])
            except Exception:
                logger.exception("Failed to close session during logout")

        logout(request)
        response = HttpResponseRedirect("/")
        response.delete_cookie("sessionid")
        return response


class PasswordResetRequestView(APIView):
    """Request password reset - send code to email."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'success': True, 'message': 'If email exists, a reset code has been sent'},
                status=status.HTTP_200_OK
            )

        PasswordResetToken.objects.filter(user=user, is_used=False).delete()

        token = PasswordResetToken.generate_token()
        expires_at = timezone.now() + timezone.timedelta(minutes=15)

        reset_token = PasswordResetToken.objects.create(
            user=user, email=email, token=token, expires_at=expires_at
        )

        subject = 'NexusIDE - Password Reset Code'
        body = (
            f'Hello {user.username},\n\n'
            f'Your password reset code is: {token}\n\n'
            f'This code will expire in 15 minutes.\n\n'
            f'If you didn\'t request a password reset, please ignore this email.\n\n'
            f'Thanks,\nNexusIDE Team'
        )

        try:
            if settings.DEBUG:
                send_mail(
                    subject, body,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            else:
                from apps.compiler.tasks import send_password_reset_email_task
                send_password_reset_email_task.delay(user.id, email, token)
            return Response(
                {'success': True, 'message': 'Password reset code sent'},
                status=status.HTTP_200_OK
            )
        except Exception:
            logger.exception("Failed to send password reset email to %s", email)
            reset_token.delete()
            return Response(
                {'error': 'Failed to send email. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordResetVerifyView(APIView):
    """Verify reset code."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        token = request.data.get('token', '').strip()

        if not email or not token:
            return Response(
                {'error': 'Email and token are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            reset_token = PasswordResetToken.objects.get(
                user=user, email=email, token=token
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'error': 'Invalid reset code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not reset_token.is_valid():
            if reset_token.attempts >= 5:
                return Response(
                    {'error': 'Too many attempts. Request a new reset code.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            elif timezone.now() > reset_token.expires_at:
                return Response(
                    {'error': 'Reset code has expired. Request a new one.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return Response(
                    {'error': 'This code has already been used'},
                    status=status.HTTP_403_FORBIDDEN
                )

        return Response(
            {'success': True, 'message': 'Code verified', 'email': email},
            status=status.HTTP_200_OK
        )


class PasswordResetCompleteView(APIView):
    """Complete password reset - set new password."""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        token = request.data.get('token', '').strip()
        new_password = request.data.get('new_password', '')

        if not all([email, token, new_password]):
            return Response(
                {'error': 'Email, token, and new password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            reset_token = PasswordResetToken.objects.get(
                user=user, email=email, token=token
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'error': 'Invalid reset code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not reset_token.is_valid():
            reset_token.increment_attempts()
            if reset_token.attempts >= 5:
                return Response(
                    {'error': 'Too many attempts. Request a new reset code.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return Response(
                {'error': 'Invalid or expired reset code'},
                status=status.HTTP_403_FORBIDDEN
            )

        user.set_password(new_password)
        user.save(update_fields=['password'])

        reset_token.mark_used()

        UserActivity.objects.create(
            user=user, activity_type='password_reset',
            description='Password was reset'
        )

        return Response(
            {'success': True, 'message': 'Password has been reset successfully.'},
            status=status.HTTP_200_OK
        )


class EmailVerificationSendView(APIView):
    """Send email verification code to user."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        email = user.email

        if not email:
            return Response(
                {'error': 'User email not found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        EmailVerificationToken.objects.filter(user=user, is_verified=False).delete()

        token = EmailVerificationToken.generate_token()
        expires_at = timezone.now() + timezone.timedelta(minutes=15)

        verification_token = EmailVerificationToken.objects.create(
            user=user, email=email, token=token, expires_at=expires_at
        )

        logger.info("Email verification requested for %s", user.username)

        subject = 'NexusIDE - Email Verification Code'
        body = (
            f'Hello {user.username},\n\n'
            f'Your email verification code is: {token}\n\n'
            f'This code will expire in 15 minutes.\n\n'
            f'If you didn\'t request email verification, please ignore this email.\n\n'
            f'Thanks,\nNexusIDE Team'
        )

        try:
            if settings.DEBUG:
                send_mail(
                    subject, body,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            else:
                from apps.compiler.tasks import send_verification_email_task
                send_verification_email_task.delay(user.id, email, token)
            return Response(
                {
                    'success': True,
                    'message': f'Verification code sent to {email}',
                },
                status=status.HTTP_200_OK
            )
        except Exception:
            logger.exception("Failed to send verification email to %s", email)
            verification_token.delete()
            return Response(
                {'error': 'Failed to send email. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EmailVerificationVerifyView(APIView):
    """Verify email with 6-digit code."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        token = request.data.get('token', '').strip()

        if not token or len(token) != 6:
            return Response(
                {'error': 'Please enter a valid 6-digit code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            verification_token = EmailVerificationToken.objects.get(
                user=user, token=token
            )
        except EmailVerificationToken.DoesNotExist:
            return Response(
                {'error': 'Invalid verification code'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not verification_token.is_valid():
            if verification_token.attempts >= 5:
                return Response(
                    {'error': 'Too many attempts. Request a new verification code.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            elif timezone.now() > verification_token.expires_at:
                return Response(
                    {'error': 'Verification code has expired. Request a new one.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            else:
                return Response(
                    {'error': 'This code has already been used'},
                    status=status.HTTP_403_FORBIDDEN
                )

        verification_token.mark_verified()

        try:
            profile = user.profile
            profile.email_verified = True
            profile.email_verified_at = timezone.now()
            profile.save(update_fields=['email_verified', 'email_verified_at'])
        except Exception:
            logger.debug("Could not update profile email_verified for %s", user.username)

        UserActivity.objects.create(
            user=user, activity_type='email_verified',
            description='Email address verified'
        )

        return Response(
            {'success': True, 'message': 'Email verified successfully!'},
            status=status.HTTP_200_OK
        )


class EmailVerificationCheckView(APIView):
    """Check if user email is verified."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.profile
            return Response({
                'email_verified': profile.email_verified,
                'email_verified_at': profile.email_verified_at,
                'email': request.user.email
            })
        except Exception:
            return Response({
                'email_verified': False,
                'email': request.user.email
            })


class UserHeartbeatView(APIView):
    """Record user heartbeat - called every minute to track active time."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        page = request.data.get('page', '')

        try:
            UserHeartbeat.objects.create(
                user=request.user, page=page, is_active=True
            )

            # Cleanup old heartbeats (keep only last 30 days)
            cutoff_date = timezone.now() - timezone.timedelta(days=30)
            UserHeartbeat.objects.filter(
                user=request.user, timestamp__lt=cutoff_date
            ).delete()

            return Response({
                'success': True,
                'message': 'Heartbeat recorded'
            }, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Failed to record heartbeat for %s", request.user.username)
            return Response({
                'error': 'Failed to record heartbeat'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserStatsView(APIView):
    """Get realistic user statistics based on actual heartbeat and activity data."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        heartbeats = UserHeartbeat.objects.filter(user=user)
        total_active_minutes = heartbeats.count()
        total_active_seconds = total_active_minutes * 60

        today = timezone.now().date()
        today_active_minutes = heartbeats.filter(timestamp__date=today).count()

        from datetime import timedelta
        week_start = timezone.now() - timedelta(days=7)
        week_active_minutes = heartbeats.filter(timestamp__gte=week_start).count()

        activities = UserActivity.objects.filter(user=user)
        activity_counts = activities.values('activity_type').annotate(count=Count('id'))

        total_hours = total_active_seconds // 3600
        total_mins = (total_active_seconds % 3600) // 60

        return Response({
            'total_active_time': f"{int(total_hours)}h {int(total_mins)}m",
            'total_active_seconds': total_active_seconds,
            'today_active_minutes': today_active_minutes,
            'week_active_minutes': week_active_minutes,
            'total_heartbeats': heartbeats.count(),
            'total_activities': activities.count(),
            'activity_breakdown': list(activity_counts),
        })
