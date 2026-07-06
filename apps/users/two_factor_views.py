"""
Two-Factor Authentication API Views
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from .two_factor import get_2fa_service
import logging

logger = logging.getLogger(__name__)


class TwoFactorSetupView(APIView):
    """Initiate 2FA setup - generates secret and QR code URI."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        POST /api/auth/2fa/setup/
        
        Response:
        {
            "secret": "JBSWY3DPEHPK3PXP",
            "provisioning_uri": "otpauth://totp/NexusIDE:user?...",
            "backup_codes": ["a1b2c3d4", ...]
        }
        """
        service = get_2fa_service()

        # Check if 2FA is already enabled
        if service.is_enabled(request.user.id):
            return Response(
                {'error': '2FA is already enabled. Disable it first.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        secret, uri, backup_codes = service.initiate_setup(request.user.id)

        return Response({
            'secret': secret,
            'provisioning_uri': uri,
            'backup_codes': backup_codes,
        }, status=status.HTTP_200_OK)


class TwoFactorVerifyView(APIView):
    """Complete 2FA setup by verifying a code."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        POST /api/auth/2fa/verify/
        Body: { "code": "123456" }
        """
        code = request.data.get('code', '').strip()

        if not code:
            return Response(
                {'error': 'Code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = get_2fa_service()

        if service.complete_setup(request.user.id, code):
            return Response({
                'success': True,
                'message': '2FA has been enabled successfully.',
            }, status=status.HTTP_200_OK)

        return Response(
            {'error': 'Invalid code. Please try again.'},
            status=status.HTTP_400_BAD_REQUEST
        )


class TwoFactorDisableView(APIView):
    """Disable 2FA (requires current 2FA code)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        POST /api/auth/2fa/disable/
        Body: { "code": "123456" }
        """
        code = request.data.get('code', '').strip()

        if not code:
            return Response(
                {'error': 'Current 2FA code is required to disable'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = get_2fa_service()

        if service.disable(request.user.id, code):
            return Response({
                'success': True,
                'message': '2FA has been disabled.',
            }, status=status.HTTP_200_OK)

        return Response(
            {'error': 'Invalid code. Cannot disable 2FA.'},
            status=status.HTTP_400_BAD_REQUEST
        )


class TwoFactorStatusView(APIView):
    """Check 2FA status for current user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        GET /api/auth/2fa/status/
        
        Response:
        {
            "enabled": true,
            "backup_codes_remaining": 7
        }
        """
        service = get_2fa_service()
        enabled = service.is_enabled(request.user.id)
        backup_codes = service.get_backup_codes(request.user.id) if enabled else []

        return Response({
            'enabled': enabled,
            'backup_codes_remaining': len(backup_codes),
        }, status=status.HTTP_200_OK)


class TwoFactorLoginVerifyView(APIView):
    """Verify 2FA code during login (public endpoint with rate limiting)."""
    permission_classes = []  # Allow unauthenticated access

    def post(self, request):
        """
        POST /api/auth/2fa/login-verify/
        Body: { "user_id": 1, "code": "123456" }
        
        This is called after password verification when 2FA is enabled.
        Rate limited to prevent brute force attacks.
        """
        from config.rate_limiter import LOGIN_LIMITER
        from config.rate_limiter import get_client_identifier

        # Apply rate limiting
        identifier = get_client_identifier(request)
        if not LOGIN_LIMITER.is_allowed(identifier):
            return Response(
                {'error': 'Too many verification attempts. Please try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        user_id = request.data.get('user_id')
        code = request.data.get('code', '').strip()

        if not user_id or not code:
            return Response(
                {'error': 'user_id and code are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        service = get_2fa_service()

        if not service.is_enabled(user_id):
            return Response(
                {'error': '2FA is not enabled for this user'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if service.verify(user_id, code):
            # Generate JWT tokens here or pass to auth flow
            return Response({
                'success': True,
                'message': '2FA verification successful',
            }, status=status.HTTP_200_OK)

        return Response(
            {'error': 'Invalid 2FA code'},
            status=status.HTTP_401_UNAUTHORIZED
        )
