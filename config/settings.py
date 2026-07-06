import os
from pathlib import Path
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured

# ── Sentry (error tracking) ──
SENTRY_DSN = os.environ.get('SENTRY_DSN', '')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
if SENTRY_DSN and not DEBUG:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration(), CeleryIntegration()],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            send_default_pii=False,
            environment='production' if not DEBUG else 'development',
        )
    except ImportError:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

# Manual .env loading
def load_env_file():
    """Load environment variables from .env file"""
    # Clear old email settings from environment
    for key in list(os.environ.keys()):
        if key.startswith('EMAIL_'):
            del os.environ[key]

    env_path = BASE_DIR / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    os.environ[key] = value

load_env_file()

# SECURITY: Fail immediately if SECRET_KEY is not set in production
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-nexusIDE-development-key-DO-NOT-USE-IN-PRODUCTION'
    else:
        raise ImproperlyConfigured(
            'SECRET_KEY environment variable is required. '
            'Set it in your .env file or environment.'
        )

ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if host.strip()]
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS must be set in production')

CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173,http://localhost:8000,http://127.0.0.1:5173').split(',') if origin.strip()]
CORS_ALLOW_CREDENTIALS = True
CORS_PREFLIGHT_MAX_AGE = 86400
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'rest_framework',
    'corsheaders',
    'drf_spectacular',
    'apps.users',
    'apps.compiler',
    'apps.projects',
    'apps.community',
    'apps.problems',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.rate_limiter.RateLimitMiddleware',  # Rate limiting
    'config.security.SecurityHeadersMiddleware',  # Security headers
    'config.security.InputSanitizationMiddleware',  # Input sanitization
    'config.security.RequestLoggingMiddleware',  # Request logging
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'apps.users.password_validators.StrongPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Data Integrity Settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
    'FORMAT_SUFFIX_PATTERNS': False,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'NexusIDE API',
    'DESCRIPTION': 'Full-stack online IDE with code execution, AI assistance, competitive programming, project management, and community features.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/',
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'Auth', 'description': 'Registration, login, token refresh'},
        {'name': 'Code Execution', 'description': 'Run code in sandboxed environments'},
        {'name': 'AI Assistant', 'description': 'AI-powered code help, chat, explain, review, debug'},
        {'name': 'Snippets', 'description': 'Code snippet CRUD'},
        {'name': 'Projects', 'description': 'Project and file management'},
        {'name': 'Community', 'description': 'Community posts, comments, likes'},
        {'name': 'Problems', 'description': 'Competitive programming problems and submissions'},
        {'name': 'Notifications', 'description': 'User notifications'},
        {'name': 'Master Dashboard', 'description': 'Admin-only metrics and management'},
        {'name': 'Health', 'description': 'System health and status'},
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(seconds=int(os.environ.get('JWT_ACCESS_TOKEN_LIFETIME', 3600))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(os.environ.get('JWT_REFRESH_TOKEN_LIFETIME', 30))),
}

# Session Settings for Persistent Login
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE', 86400))  # Default 1 day
SESSION_COOKIE_PERSISTENT = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_NAME = 'nexusIDE_sessionid'
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = not DEBUG
X_FRAME_OPTIONS = 'DENY' if not DEBUG else 'SAMEORIGIN'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Caching Configuration - Redis for production, LocMem for development
REDIS_URL = os.environ.get('REDIS_URL', '')
if REDIS_URL and not DEBUG:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'MAX_ENTRIES': 10000,
            },
            'KEY_PREFIX': 'nexuside',
            'TIMEOUT': 300,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'nexuside-cache',
            'OPTIONS': {
                'MAX_ENTRIES': 10000,
            },
            'KEY_PREFIX': 'nexuside',
            'TIMEOUT': 300,
        }
    }

# Database connection - Auto-detect from DB_ENGINE in .env
# Uses Django's built-in connection pooling via CONN_MAX_AGE
db_engine = os.environ.get('DB_ENGINE', 'django.db.backends.postgresql')

if 'postgresql' in db_engine:
    # PostgreSQL for production/performance
    # Connection pooling handled via CONN_MAX_AGE (persistent connections)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'nexuside_db'),
            'USER': os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '600')),  # 10 min persistent connections
            'CONN_HEALTH_CHECKS': True,  # Enable health checks (Django 4.1+)
            'ATOMIC_REQUESTS': False,  # Better concurrency
            'AUTOCOMMIT': True,  # Autocommit mode for better performance
            'OPTIONS': {
                'connect_timeout': 10,
                'options': '-c statement_timeout=30000',  # 30s query timeout
            },
        }
    }
else:
    # SQLite for development (fallback)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Master Admin — only this username can access the master dashboard
MASTER_ADMIN_USERNAME = os.environ.get('MASTER_ADMIN_USERNAME', 'ADMIN')

# Code execution limits (env-configurable)
EXECUTION_TIMEOUT = int(os.environ.get('EXECUTION_TIMEOUT', '30'))
EXECUTION_MEMORY_LIMIT = int(os.environ.get('EXECUTION_MEMORY_LIMIT', '512'))
MAX_CODE_SIZE = int(os.environ.get('MAX_CODE_SIZE', '1000000'))

# SECURITY: Docker Sandbox Configuration
DOCKER_ENABLED = os.environ.get('DOCKER_ENABLED', 'False').lower() == 'true'
DOCKER_SOCKET = os.environ.get('DOCKER_SOCKET', '/var/run/docker.sock')

# Docker Resource Limits (per container)
DOCKER_RESOURCE_LIMITS = {
    'python': {
        'memory': '256m',
        'memswap_limit': '512m',
        'cpu_quota': 100000,    # 0.1 cores
        'cpu_period': 100000,
        'pids_limit': 64,       # Max 64 processes
        'timeout': 30,          # seconds
    },
    'c': {
        'memory': '128m',
        'memswap_limit': '256m',
        'cpu_quota': 100000,
        'cpu_period': 100000,
        'pids_limit': 32,
        'timeout': 10,
    },
    'cpp': {
        'memory': '128m',
        'memswap_limit': '256m',
        'cpu_quota': 100000,
        'cpu_period': 100000,
        'pids_limit': 32,
        'timeout': 10,
    }
}

# AI Configuration - Multi-Provider Support
# Primary models: DeepSeek R1 (reasoning), Qwen3 (coding)
# Fallback models: OpenAI, Claude, OpenRouter, NVIDIA NIM

# New AI providers (2025 upgrade)
DEEPSEEK_R1_API_KEY = os.environ.get('DEEPSEEK_R1_API_KEY', '')  # For debugging/reasoning
QWEN3_API_KEY = os.environ.get('QWEN3_API_KEY', '')              # For code generation
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
NVIDIA_NIM_API_KEY = os.environ.get('NVIDIA_NIM_API_KEY', '')
NVIDIA_NIM_BASE_URL = os.environ.get('NVIDIA_NIM_BASE_URL', 'https://integrate.api.nvidia.com/v1')

# Legacy providers (kept for backward compatibility)
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'openai')  # openai or claude
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
ANTHROPIC_MODEL = os.environ.get('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')

# Model configuration
AI_MAX_TOKENS = int(os.environ.get('AI_MAX_TOKENS', '2048'))
AI_TEMPERATURE = float(os.environ.get('AI_TEMPERATURE', '0.7'))
AI_TIMEOUT = int(os.environ.get('AI_TIMEOUT', '30'))

# Multi-Provider routing configuration
AI_ENABLED_PROVIDERS = [
    'deepseek_r1',   # PRIMARY: Debugging & reasoning
    'qwen3',         # PRIMARY: Code generation & chat
    'openai',        # FALLBACK: General purpose
    'openrouter',    # FALLBACK: Universal gateway
]

# Task-specific model preferences
AI_TASK_MODEL_PREFERENCES = {
    'bug_diagnosis': ['deepseek_r1', 'qwen3', 'claude'],
    'code_review': ['deepseek_r1', 'qwen3', 'claude'],
    'optimization': ['deepseek_r1', 'qwen3', 'openai'],
    'auto_fix': ['qwen3', 'deepseek_r1', 'openai'],
    'code_generation': ['qwen3', 'openai', 'deepseek_r1'],
    'refactoring': ['qwen3', 'openai', 'deepseek_r1'],
    'explanation': ['qwen3', 'openai', 'claude'],
    'chat': ['qwen3', 'openai', 'claude'],
}

# RAG Configuration (Retrieval-Augmented Generation)
RAG_ENABLED = os.environ.get('RAG_ENABLED', 'True').lower() == 'true'
RAG_MAX_CONTEXT_TOKENS = 4000
RAG_MAX_FILES = 5

# Rate Limiting
RATE_LIMIT_EXECUTION = 10  # requests per minute
RATE_LIMIT_API = 100  # requests per hour
RATE_LIMIT_LOGIN = 5  # attempts per 5 minutes
RATE_LIMIT_SUBMISSION = 50  # submissions per hour

# Logging Configuration
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'django.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 5,  # 5MB
            'backupCount': 5,
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'security.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# Database Backup Settings
DB_BACKUP_DIR = BASE_DIR / 'backups'
DB_BACKUP_DIR.mkdir(exist_ok=True)
DB_BACKUP_RETENTION_DAYS = 30

# Email Configuration for Password Reset
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'NexusIDE <noreply@nexuside.dev>')

# ── Celery Configuration ──
CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

# ── Django Channels Configuration ──
ASGI_APPLICATION = 'config.asgi.application'
if os.environ.get('REDIS_URL'):
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [os.environ.get('REDIS_URL', 'redis://localhost:6379/0')],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# ── Celery Beat Schedule ──
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-heartbeats': {
        'task': 'apps.compiler.tasks.cleanup_old_heartbeats',
        'schedule': timedelta(hours=24),
    },
    'cleanup-expired-api-keys': {
        'task': 'apps.compiler.tasks.cleanup_expired_api_keys',
        'schedule': timedelta(hours=6),
    },
    'cleanup-old-executions': {
        'task': 'apps.compiler.tasks.cleanup_old_executions',
        'schedule': timedelta(hours=24),
    },
}
