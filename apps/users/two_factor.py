"""
Two-Factor Authentication (2FA) using TOTP.
Adds an extra layer of security to user accounts.
"""
import secrets
import hashlib
import hmac
import base64
import struct
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class TOTPService:
    """
    Time-based One-Time Password (TOTP) service.
    Implements RFC 6238 for 2FA.
    """

    def __init__(self):
        self.issuer = 'NexusIDE'
        self.digits = 6
        self.period = 30  # seconds
        self.drift = 1  # allow 1 period drift

    def generate_secret(self) -> str:
        """Generate a cryptographically secure secret key."""
        return base64.b32encode(secrets.token_bytes(20)).decode('utf-8')

    def _generate_totp(self, secret: str, timestamp: int) -> str:
        """Generate TOTP code for given timestamp."""
        # Decode secret
        key = base64.b32decode(secret, casefold=True)

        # Calculate time step
        time_step = timestamp // self.period

        # Convert to bytes
        time_bytes = struct.pack('>Q', time_step)

        # HMAC-SHA1
        hmac_obj = hmac.new(key, time_bytes, hashlib.sha1)
        digest = hmac_obj.digest()

        # Dynamic truncation
        offset = digest[-1] & 0x0F
        truncated = struct.unpack('>I', digest[offset:offset + 4])[0]
        truncated &= 0x7FFFFFFF

        # Generate code
        code = truncated % (10 ** self.digits)
        return str(code).zfill(self.digits)

    def get_current_code(self, secret: str) -> str:
        """Get the current TOTP code."""
        return self._generate_totp(secret, int(time.time()))

    def verify_code(self, secret: str, code: str, window: int = None) -> bool:
        """
        Verify a TOTP code.
        Allows for time drift (default: 1 period = 30 seconds).
        """
        if window is None:
            window = self.drift

        current_time = int(time.time())

        # Check current and adjacent time steps
        for i in range(-window, window + 1):
            expected = self._generate_totp(secret, current_time + (i * self.period))
            if hmac.compare_digest(code, expected):
                return True

        return False

    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """Generate QR code URI for authenticator apps."""
        import urllib.parse
        params = {
            'secret': secret,
            'issuer': self.issuer,
            'algorithm': 'SHA1',
            'digits': str(self.digits),
            'period': str(self.period),
        }
        query = urllib.parse.urlencode(params)
        return f'otpauth://totp/{self.issuer}:{urllib.parse.quote(email)}?{query}'


class TwoFactorService:
    """Manages 2FA state for users."""

    SETUP_CACHE_KEY = '2fa_setup:{}'
    BACKUP_CODES_KEY = '2fa_backup:{}'
    ENABLED_KEY = '2fa_enabled:{}'

    def __init__(self):
        self.totp = TOTPService()

    def initiate_setup(self, user_id: int) -> Tuple[str, str, str]:
        """
        Start 2FA setup for a user.
        Returns: (secret, provisioning_uri, backup_codes)
        """
        secret = self.totp.generate_secret()
        provisioning_uri = self.totp.get_provisioning_uri(secret, f'user_{user_id}')

        # Generate backup codes
        backup_codes = [secrets.token_hex(4) for _ in range(8)]

        # Store temporarily (not enabled yet)
        cache_key = self.SETUP_CACHE_KEY.format(user_id)
        cache.set(cache_key, {
            'secret': secret,
            'backup_codes': backup_codes,
            'created_at': datetime.now().isoformat(),
        }, timeout=600)  # 10 minutes to complete setup

        return secret, provisioning_uri, backup_codes

    def complete_setup(self, user_id: int, code: str) -> bool:
        """
        Complete 2FA setup after user verifies a code.
        Returns True if setup was successful.
        """
        cache_key = self.SETUP_CACHE_KEY.format(user_id)
        setup_data = cache.get(cache_key)

        if not setup_data:
            return False

        # Verify the code
        if not self.totp.verify_code(setup_data['secret'], code):
            return False

        # Enable 2FA
        self._enable_2fa(user_id, setup_data['secret'], setup_data['backup_codes'])
        cache.delete(cache_key)

        logger.info(f"2FA enabled for user {user_id}")
        return True

    def _enable_2fa(self, user_id: int, secret: str, backup_codes: list):
        """Store 2FA configuration."""
        # Store enabled status
        enabled_key = self.ENABLED_KEY.format(user_id)
        cache.set(enabled_key, True, timeout=None)  # No expiry

        # Store backup codes
        backup_key = self.BACKUP_CODES_KEY.format(user_id)
        # Hash backup codes for security
        hashed_codes = [
            hashlib.sha256(code.encode()).hexdigest()
            for code in backup_codes
        ]
        cache.set(backup_key, hashed_codes, timeout=None)

        # Also store the secret (encrypted in production)
        secret_key = f'2fa_secret:{user_id}'
        cache.set(secret_key, secret, timeout=None)

    def is_enabled(self, user_id: int) -> bool:
        """Check if 2FA is enabled for a user."""
        enabled_key = self.ENABLED_KEY.format(user_id)
        return cache.get(enabled_key, False)

    def verify(self, user_id: int, code: str) -> bool:
        """
        Verify a 2FA code during login.
        Also checks backup codes.
        """
        # Check TOTP code
        secret_key = f'2fa_secret:{user_id}'
        secret = cache.get(secret_key)

        if secret and self.totp.verify_code(secret, code):
            return True

        # Check backup codes
        backup_key = self.BACKUP_CODES_KEY.format(user_id)
        backup_codes = cache.get(backup_key, [])

        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if code_hash in backup_codes:
            # Remove used backup code
            backup_codes.remove(code_hash)
            cache.set(backup_key, backup_codes, timeout=None)
            logger.info(f"Backup code used for user {user_id}")
            return True

        return False

    def disable(self, user_id: int, code: str) -> bool:
        """
        Disable 2FA (requires current 2FA code for security).
        """
        if not self.verify(user_id, code):
            return False

        # Remove all 2FA data
        cache.delete(self.ENABLED_KEY.format(user_id))
        cache.delete(self.BACKUP_CODES_KEY.format(user_id))
        cache.delete(f'2fa_secret:{user_id}')

        logger.info(f"2FA disabled for user {user_id}")
        return True

    def get_backup_codes(self, user_id: int) -> list:
        """Get remaining backup codes (hashed)."""
        backup_key = self.BACKUP_CODES_KEY.format(user_id)
        return cache.get(backup_key, [])


# Singleton
_2fa_service = None


def get_2fa_service() -> TwoFactorService:
    """Get the 2FA service instance."""
    global _2fa_service
    if _2fa_service is None:
        _2fa_service = TwoFactorService()
    return _2fa_service
