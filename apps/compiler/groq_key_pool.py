"""
Groq API Key Pool — manages multiple API keys with smart rotation.

Each key has its own RPM/RPD counters. When a key hits its limit,
the pool automatically switches to the next available key.

Rate limits (Groq free tier):
  - RPM: 30 requests/minute (rolling 60s window)
  - RPD: 1,000 requests/day (resets at midnight UTC)
  - TPM: 6,000 tokens/minute (rolling 60s window)
"""

import os
import time
import threading
import logging
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger(__name__)

# Groq free tier limits per key
GROQ_RPM_LIMIT = 30       # requests per minute
GROQ_RPD_LIMIT = 1000     # requests per day
GROQ_TPM_LIMIT = 6000     # tokens per minute


class KeyState:
    """Tracks usage state for a single API key."""

    __slots__ = ('key', 'name', 'rpm_timestamps', 'tpm_tokens', 'rpd_count',
                 'rpd_date', 'consecutive_failures', 'total_requests',
                 'total_failures', 'last_used', 'last_error', 'cooldown_until',
                 'reserved_count')

    def __init__(self, key, name=''):
        self.key = key
        self.name = name or key[:12] + '...'
        self.rpm_timestamps = deque()         # timestamps of recent requests (for RPM)
        self.tpm_tokens = deque()             # (timestamp, token_count) for TPM
        self.rpd_count = 0                    # requests today
        self.rpd_date = self._today_utc()     # date for RPD reset
        self.consecutive_failures = 0
        self.total_requests = 0
        self.total_failures = 0
        self.last_used = 0
        self.last_error = ''
        self.cooldown_until = 0               # timestamp when key becomes available again
        self.reserved_count = 0               # in-flight requests using this key

    @staticmethod
    def _today_utc():
        return datetime.now(timezone.utc).strftime('%Y-%m-%d')

    def _clean_rpm(self):
        """Remove timestamps older than 60 seconds."""
        cutoff = time.time() - 60
        while self.rpm_timestamps and self.rpm_timestamps[0] < cutoff:
            self.rpm_timestamps.popleft()

    def _clean_tpm(self):
        """Remove token counts older than 60 seconds."""
        cutoff = time.time() - 60
        while self.tpm_tokens and self.tpm_tokens[0][0] < cutoff:
            self.tpm_tokens.popleft()

    def _reset_rpd_if_new_day(self):
        """Reset RPD counter if it's a new day (UTC)."""
        today = self._today_utc()
        if self.rpd_date != today:
            self.rpd_count = 0
            self.rpd_date = today

    def record_request(self, tokens_used=0):
        """Record a completed request against this key."""
        now = time.time()
        self.rpm_timestamps.append(now)
        if tokens_used > 0:
            self.tpm_tokens.append((now, tokens_used))
        self.rpd_count += 1
        self.total_requests += 1
        self.last_used = now
        self.consecutive_failures = 0
        self.reserved_count = max(0, self.reserved_count - 1)

    def record_failure(self, error=''):
        """Record a failed request (releases reservation)."""
        self.consecutive_failures += 1
        self.total_failures += 1
        self.last_error = error
        self.reserved_count = max(0, self.reserved_count - 1)
        now = time.time()

        if '429' in str(error) or 'rate' in str(error).lower():
            # Rate limit hit — cooldown for 10 seconds (RPM window will reset in <60s)
            self.cooldown_until = now + 10
        elif self.consecutive_failures >= 3:
            # Too many failures — cooldown for 30 seconds
            self.cooldown_until = now + 30
            self.consecutive_failures = 0

    @property
    def rpm_available(self):
        """Remaining requests this minute (including in-flight reservations)."""
        self._clean_rpm()
        effective = len(self.rpm_timestamps) + self.reserved_count
        return max(0, GROQ_RPM_LIMIT - effective)

    @property
    def tpm_available(self):
        """Remaining tokens this minute."""
        self._clean_tpm()
        used = sum(t for _, t in self.tpm_tokens)
        return max(0, GROQ_TPM_LIMIT - used)

    @property
    def rpd_available(self):
        """Remaining requests today."""
        self._reset_rpd_if_new_day()
        return max(0, GROQ_RPD_LIMIT - self.rpd_count)

    @property
    def is_available(self):
        """Check if this key can handle a request right now."""
        now = time.time()
        if now < self.cooldown_until:
            return False
        self._clean_rpm()
        self._reset_rpd_if_new_day()
        return self.rpm_available > 0 and self.rpd_available > 0

    @property
    def score(self):
        """Higher score = more available capacity. Used for key selection."""
        if not self.is_available:
            return -1
        # Weighted: RPM (40%) + RPD (40%) + TPM (20%)
        rpm_score = self.rpm_available / GROQ_RPM_LIMIT
        rpd_score = self.rpd_available / GROQ_RPD_LIMIT
        tpm_score = self.tpm_available / GROQ_TPM_LIMIT
        return (rpm_score * 0.4) + (rpd_score * 0.4) + (tpm_score * 0.2)

    def to_dict(self):
        """Return key stats as dict (for API/debug)."""
        self._clean_rpm()
        return {
            'name': self.name,
            'available': self.is_available,
            'rpm': f'{self.rpm_available}/{GROQ_RPM_LIMIT}',
            'rpd': f'{self.rpd_available}/{GROQ_RPD_LIMIT}',
            'tpm': f'{self.tpm_available}/{GROQ_TPM_LIMIT}',
            'in_flight': self.reserved_count,
            'score': round(self.score, 3),
            'total_requests': self.total_requests,
            'total_failures': self.total_failures,
            'last_error': self.last_error,
        }


class GroqKeyPool:
    """
    Manages a pool of Groq API keys with smart rotation.

    Usage:
        pool = GroqKeyPool()
        pool.load_from_env()

        # Get best available key
        key = pool.get_key()
        if key:
            # Use the key with Groq API
            ...
            pool.record_success(key)
        else:
            # All keys exhausted
            ...

    Thread-safe: all operations are protected by a lock.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton — one pool shared across the app."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.keys = []          # list of KeyState objects
        self._index = 0         # round-robin pointer
        self._lock = threading.Lock()

    def load_from_env(self):
        """
        Load keys from environment variables.

        Supports two formats in .env:
          GROQ_API_KEYS=key1,key2,key3
          GROQ_API_KEY=key1  (single key, legacy)
          GROQ_KEY_NAMES=name1,name2,name3  (optional labels)
        """
        keys_str = os.environ.get('GROQ_API_KEYS', '')
        single_key = os.environ.get('GROQ_API_KEY', '')
        names_str = os.environ.get('GROQ_KEY_NAMES', '')

        names = [n.strip() for n in names_str.split(',') if n.strip()] if names_str else []

        raw_keys = []
        if keys_str:
            raw_keys = [k.strip() for k in keys_str.split(',') if k.strip()]
        elif single_key:
            raw_keys = [single_key.strip()]

        if not raw_keys:
            logger.warning("GroqKeyPool: No API keys found in environment")
            return

        self.keys = []
        for i, key in enumerate(raw_keys):
            name = names[i] if i < len(names) else f'Key #{i+1}'
            self.keys.append(KeyState(key, name))

        logger.info("GroqKeyPool: Loaded %d keys", len(self.keys))

    def get_key(self):
        """
        Atomically reserve the best available key.

        The key is reserved (reserved_count++) BEFORE the lock is released,
        preventing other threads from picking the same key.
        """
        with self._lock:
            if not self.keys:
                return None

            available = [k for k in self.keys if k.is_available]
            if not available:
                logger.warning("GroqKeyPool: All %d keys exhausted", len(self.keys))
                return None

            # Pick key with highest score
            best = max(available, key=lambda k: k.score)
            # Atomically reserve it — other threads will see reduced rpm_available
            best.reserved_count += 1
            return best

    def get_key_for_user(self, user_id):
        """
        Reserve a key for a specific user.

        Assigns a consistent key to each user (hash-based),
        but falls back to best-available if that key is exhausted.
        """
        with self._lock:
            if not self.keys:
                return None

            # Hash user_id to assign a preferred key
            preferred_idx = hash(str(user_id)) % len(self.keys)
            preferred = self.keys[preferred_idx]

            if preferred.is_available:
                preferred.reserved_count += 1
                return preferred

            # Preferred key exhausted — find best available
            available = [k for k in self.keys if k.is_available]
            if not available:
                return None

            best = max(available, key=lambda k: k.score)
            best.reserved_count += 1
            return best

    def record_success(self, key_state, tokens_used=0):
        """Record a successful request."""
        with self._lock:
            key_state.record_request(tokens_used)

    def record_failure(self, key_state, error=''):
        """Record a failed request (rate limit, network, etc)."""
        with self._lock:
            key_state.record_failure(error)

    def release_key(self, key_state):
        """Release a reservation without recording a request (abandoned/cancelled)."""
        with self._lock:
            key_state.reserved_count = max(0, key_state.reserved_count - 1)

    def get_stats(self):
        """Return stats for all keys."""
        with self._lock:
            return [k.to_dict() for k in self.keys]

    def get_available_count(self):
        """Return number of currently available keys."""
        with self._lock:
            return sum(1 for k in self.keys if k.is_available)

    def get_total_rpd_capacity(self):
        """Return total remaining RPD across all keys."""
        with self._lock:
            return sum(k.rpd_available for k in self.keys)

    def reset_all(self):
        """Reset all key states (for testing)."""
        with self._lock:
            for k in self.keys:
                k.rpm_timestamps.clear()
                k.tpm_tokens.clear()
                k.rpd_count = 0
                k.rpd_date = k._today_utc()
                k.consecutive_failures = 0
                k.cooldown_until = 0


# Convenience singleton accessor
def get_groq_pool():
    """Get or create the Groq key pool singleton."""
    pool = GroqKeyPool()
    if not pool.keys:
        pool.load_from_env()
    return pool
