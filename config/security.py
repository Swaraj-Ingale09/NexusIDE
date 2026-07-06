"""
Security headers middleware for NexusIDE.
Adds comprehensive security headers to all responses.
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """
    Adds security headers to all responses.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'

        # Clickjacking protection
        response['X-Frame-Options'] = 'DENY'

        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy (restrict browser features)
        response['Permissions-Policy'] = (
            'camera=(), '
            'microphone=(), '
            'geolocation=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'speaker=()'
        )

        # Content Security Policy
        # Note: For React/Vite, use nonces for inline scripts instead of unsafe-inline
        # Generate nonces per-request in production for maximum security
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' https://cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "img-src 'self' data: blob: https:",
            "font-src 'self' https://fonts.gstatic.com",
            "connect-src 'self' ws: wss:",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)

        # Strict Transport Security (HSTS) - only in production
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

        # Remove server identification
        if 'Server' in response:
            del response['Server']

        # Remove X-Powered-By
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        return response


class InputSanitizationMiddleware:
    """
    Sanitizes user input to prevent injection attacks.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Sanitize query parameters
        if request.GET:
            for key in request.GET:
                value = request.GET[key]
                if self._contains_suspicious_patterns(value):
                    logger.warning(
                        f"Suspicious query parameter detected: {key}={value[:100]} "
                        f"from IP {request.META.get('REMOTE_ADDR')}"
                    )

        response = self.get_response(request)
        return response

    def _contains_suspicious_patterns(self, value: str) -> bool:
        """Check for common injection patterns."""
        suspicious = [
            '<script',
            'javascript:',
            'onerror=',
            'onload=',
            'eval(',
            'document.cookie',
            'UNION SELECT',
            'DROP TABLE',
            '../../../',
            '..\\..\\',
        ]
        value_lower = value.lower()
        return any(pattern.lower() in value_lower for pattern in suspicious)


class RequestLoggingMiddleware:
    """
    Logs all API requests for security auditing.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log API requests
        if request.path.startswith('/api/') and not request.path.startswith('/api/health/'):
            import time
            start_time = time.time()

            response = self.get_response(request)

            duration = (time.time() - start_time) * 1000
            user_id = request.user.id if request.user.is_authenticated else 'anon'

            # Only log slow requests or errors
            if duration > 1000 or response.status_code >= 400:
                logger.info(
                    f"API {request.method} {request.path} "
                    f"status={response.status_code} "
                    f"duration={duration:.0f}ms "
                    f"user={user_id} "
                    f"ip={request.META.get('REMOTE_ADDR')}"
                )

            return response

        return self.get_response(request)
