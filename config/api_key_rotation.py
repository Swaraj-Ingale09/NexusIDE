"""
API Key Rotation Utility for NexusIDE
Provides secure key rotation without downtime.
"""
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class APIKeyRotation:
    """
    Manages API key rotation with support for:
    - JWT secret rotation
    - API key versioning
    - Graceful transition periods
    """

    def __init__(self, keys_dir: Optional[Path] = None):
        self.keys_dir = keys_dir or Path(__file__).parent.parent.parent / 'keys'
        self.keys_dir.mkdir(exist_ok=True)
        self.keys_file = self.keys_dir / 'api_keys.json'
        self._load_keys()

    def _load_keys(self):
        """Load existing keys from file."""
        import json
        if self.keys_file.exists():
            with open(self.keys_file, 'r') as f:
                self.keys = json.load(f)
        else:
            self.keys = {
                'jwt_secrets': [],
                'api_keys': [],
                'rotation_history': []
            }
            self._save_keys()

    def _save_keys(self):
        """Save keys to file."""
        import json
        with open(self.keys_file, 'w') as f:
            json.dump(self.keys, f, indent=2, default=str)

    def generate_jwt_secret(self) -> str:
        """Generate a new JWT secret."""
        return secrets.token_hex(64)

    def rotate_jwt_secret(self, grace_period_hours: int = 24) -> Tuple[str, str]:
        """
        Rotate JWT secret with grace period.
        
        Returns:
            Tuple of (new_secret, old_secret)
        """
        new_secret = self.generate_jwt_secret()
        old_secret = self.keys['jwt_secrets'][-1]['secret'] if self.keys['jwt_secrets'] else None

        # Add new secret with activation time
        self.keys['jwt_secrets'].append({
            'secret': new_secret,
            'created_at': datetime.now().isoformat(),
            'activates_at': (datetime.now() + timedelta(hours=grace_period_hours)).isoformat(),
            'is_active': True
        })

        # Mark old secret for deactivation
        if self.keys['jwt_secrets'] and len(self.keys['jwt_secrets']) > 1:
            self.keys['jwt_secrets'][-2]['deactivates_at'] = (
                datetime.now() + timedelta(hours=grace_period_hours)
            ).isoformat()

        # Keep only last 3 secrets
        if len(self.keys['jwt_secrets']) > 3:
            self.keys['jwt_secrets'] = self.keys['jwt_secrets'][-3:]

        self.keys['rotation_history'].append({
            'type': 'jwt_secret',
            'action': 'rotate',
            'timestamp': datetime.now().isoformat()
        })

        self._save_keys()
        logger.info("JWT secret rotated successfully")
        return new_secret, old_secret

    def get_current_jwt_secret(self) -> str:
        """Get the current active JWT secret."""
        now = datetime.now()
        
        for key_data in reversed(self.keys['jwt_secrets']):
            activates_at = datetime.fromisoformat(key_data['activates_at'])
            deactivates_at = key_data.get('deactivates_at')
            
            if now >= activates_at:
                if deactivates_at is None or now < datetime.fromisoformat(deactivates_at):
                    return key_data['secret']
        
        # Fallback to environment variable
        return os.environ.get('SECRET_KEY', secrets.token_hex(64))

    def generate_api_key(self, name: str, expires_days: int = 90) -> str:
        """
        Generate a new API key.
        
        Args:
            name: Name/identifier for the key
            expires_days: Days until key expires
            
        Returns:
            Generated API key
        """
        api_key = f"nxi_{secrets.token_hex(32)}"
        
        self.keys['api_keys'].append({
            'name': name,
            'key_hash': hashlib.sha256(api_key.encode()).hexdigest(),
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=expires_days)).isoformat(),
            'is_active': True
        })
        
        self.keys['rotation_history'].append({
            'type': 'api_key',
            'action': 'create',
            'name': name,
            'timestamp': datetime.now().isoformat()
        })
        
        self._save_keys()
        logger.info(f"API key '{name}' generated")
        return api_key

    def verify_api_key(self, api_key: str) -> bool:
        """Verify an API key is valid and not expired."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        for key_data in self.keys['api_keys']:
            if key_data['key_hash'] == key_hash:
                if not key_data['is_active']:
                    return False
                
                expires_at = datetime.fromisoformat(key_data['expires_at'])
                if datetime.now() > expires_at:
                    key_data['is_active'] = False
                    self._save_keys()
                    return False
                
                return True
        
        return False

    def revoke_api_key(self, name: str) -> bool:
        """Revoke an API key by name."""
        for key_data in self.keys['api_keys']:
            if key_data['name'] == name:
                key_data['is_active'] = False
                
                self.keys['rotation_history'].append({
                    'type': 'api_key',
                    'action': 'revoke',
                    'name': name,
                    'timestamp': datetime.now().isoformat()
                })
                
                self._save_keys()
                logger.info(f"API key '{name}' revoked")
                return True
        
        return False

    def get_active_keys_count(self) -> int:
        """Get count of active API keys."""
        return sum(1 for k in self.keys['api_keys'] if k['is_active'])

    def cleanup_expired_keys(self) -> int:
        """Remove expired API keys."""
        now = datetime.now()
        initial_count = len(self.keys['api_keys'])
        
        self.keys['api_keys'] = [
            k for k in self.keys['api_keys']
            if datetime.fromisoformat(k['expires_at']) > now
        ]
        
        removed_count = initial_count - len(self.keys['api_keys'])
        if removed_count > 0:
            self.keys['rotation_history'].append({
                'type': 'api_key',
                'action': 'cleanup',
                'removed_count': removed_count,
                'timestamp': now.isoformat()
            })
            self._save_keys()
            logger.info(f"Cleaned up {removed_count} expired API keys")
        
        return removed_count


# Singleton instance
_key_rotation = None


def get_key_rotation() -> APIKeyRotation:
    """Get the singleton APIKeyRotation instance."""
    global _key_rotation
    if _key_rotation is None:
        _key_rotation = APIKeyRotation()
    return _key_rotation
