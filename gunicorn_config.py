"""
Gunicorn production configuration for NexusIDE.
Usage: gunicorn config.wsgi:application -c gunicorn_config.py
"""
import os
import multiprocessing

# Server socket
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
backlog = int(os.environ.get('GUNICORN_BACKLOG', '2048'))

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'gthread'
threads = int(os.environ.get('GUNICORN_THREADS', '4'))
worker_connections = int(os.environ.get('GUNICORN_WORKER_CONNECTIONS', '1000'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '120'))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '5'))

# Restart workers periodically to prevent memory leaks
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '50'))

# Logging
accesslog = os.environ.get('GUNICORN_ACCESS_LOG', 'logs/gunicorn_access.log')
errorlog = os.environ.get('GUNICORN_ERROR_LOG', 'logs/gunicorn_error.log')
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'nexuside'

# Security
limit_request_line = int(os.environ.get('GUNICORN_LIMIT_REQUEST_LINE', '8190'))
limit_request_fields = int(os.environ.get('GUNICORN_LIMIT_REQUEST_FIELDS', '100'))
limit_request_field_size = int(os.environ.get('GUNICORN_LIMIT_REQUEST_FIELD_SIZE', '8190'))

# Server mechanics
preload_app = True
daemon = False
tmp_upload_dir = None

# SSL (optional - use reverse proxy in production)
certfile = os.environ.get('GUNICORN_CERTFILE')
keyfile = os.environ.get('GUNICORN_KEYFILE')

# Hook for worker initialization
def on_starting(server):
    """Called just before the master process is initialized."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forked child, re-executing.")

def worker_exit(server, worker):
    """Called when a worker exits."""
    server.log.info("Worker exited (pid: %s)", worker.pid)
