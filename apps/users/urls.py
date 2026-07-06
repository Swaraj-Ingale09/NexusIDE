from django.urls import path
from apps.users.views import (
    UserProfileView, AdminDashboardView, AdminUsersDetailView,
    AdminUserDetailView, AdminActivityLogView, UserActivityTrackingView,
    UserSatisfactionView, MasterAdminVerifyView, MasterAdminDashboardView,
    MasterAdminLogoutView, LogoutView, PasswordResetRequestView,
    PasswordResetVerifyView, PasswordResetCompleteView,
    EmailVerificationSendView, EmailVerificationVerifyView, EmailVerificationCheckView,
    UserHeartbeatView, UserStatsView
)
from apps.users.master_dashboard_views import (
    MasterDashboardMetricsView, MasterDashboardUsersView,
    MasterDashboardAPIMonitorView, MasterDashboardSystemHealthView,
    MasterDashboardUserDetailView
)
from apps.users.notification_views import NotificationViewSet
from apps.users.two_factor_views import (
    TwoFactorSetupView, TwoFactorVerifyView, TwoFactorDisableView,
    TwoFactorStatusView, TwoFactorLoginVerifyView
)

app_name = 'users'

urlpatterns = [
    path('logout/', LogoutView.as_view(), name='logout'),

    # 2FA APIs
    path('api/auth/2fa/setup/', TwoFactorSetupView.as_view(), name='2fa-setup'),
    path('api/auth/2fa/verify/', TwoFactorVerifyView.as_view(), name='2fa-verify'),
    path('api/auth/2fa/disable/', TwoFactorDisableView.as_view(), name='2fa-disable'),
    path('api/auth/2fa/status/', TwoFactorStatusView.as_view(), name='2fa-status'),
    path('api/auth/2fa/login-verify/', TwoFactorLoginVerifyView.as_view(), name='2fa-login-verify'),

    # Notifications API
    path('api/notifications/', NotificationViewSet.as_view({'get': 'list', 'post': 'list'}), name='notifications-list'),
    path('api/notifications/mark-read/', NotificationViewSet.as_view({'post': 'mark_read'}), name='notifications-mark-read'),
    path('api/notifications/mark-all-read/', NotificationViewSet.as_view({'post': 'mark_all_read'}), name='notifications-mark-all-read'),
    path('api/notifications/unread-count/', NotificationViewSet.as_view({'get': 'unread_count'}), name='notifications-unread-count'),

    # Password Reset APIs
    path('api/password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('api/password-reset/verify/', PasswordResetVerifyView.as_view(), name='password_reset_verify'),
    path('api/password-reset/complete/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Email Verification APIs
    path('api/email-verification/send/', EmailVerificationSendView.as_view(), name='email_verification_send'),
    path('api/email-verification/verify/', EmailVerificationVerifyView.as_view(), name='email_verification_verify'),
    path('api/email-verification/check/', EmailVerificationCheckView.as_view(), name='email_verification_check'),

    # User Activity & Stats APIs
    path('api/heartbeat/', UserHeartbeatView.as_view(), name='user_heartbeat'),
    path('api/stats/', UserStatsView.as_view(), name='user_stats'),

    # Master Admin Portal
    path('master/verify/', MasterAdminVerifyView.as_view(), name='master_admin_verify'),
    path('master/dashboard/', MasterAdminDashboardView.as_view(), name='master_admin_dashboard'),
    path('master/logout/', MasterAdminLogoutView.as_view(), name='master_admin_logout'),

    # Master Dashboard APIs
    path('api/master/metrics/', MasterDashboardMetricsView.as_view(), name='master_metrics'),
    path('api/master/users/', MasterDashboardUsersView.as_view(), name='master_users'),
    path('api/master/users/<int:user_id>/', MasterDashboardUserDetailView.as_view(), name='master_user_detail'),
    path('api/master/api-monitor/', MasterDashboardAPIMonitorView.as_view(), name='master_api_monitor'),
    path('api/master/health/', MasterDashboardSystemHealthView.as_view(), name='master_health'),

    # Admin Dashboard APIs
    path('api/admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('api/admin/users/', AdminUsersDetailView.as_view(), name='admin_users'),
    path('api/admin/users/<int:user_id>/', AdminUserDetailView.as_view(), name='admin_user_detail'),
    path('api/admin/activities/', AdminActivityLogView.as_view(), name='admin_activities'),

    # User Tracking APIs
    path('activity/track/', UserActivityTrackingView.as_view(), name='track_activity'),
    path('satisfaction/', UserSatisfactionView.as_view(), name='satisfaction'),
]
