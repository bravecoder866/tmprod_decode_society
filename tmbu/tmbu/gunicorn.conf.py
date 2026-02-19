"""
Copyright (c) 2024-2025 Qu Zhi
All Rights Reserved.

This software is proprietary and confidential.
Unauthorized copying, distribution, or modification of this software is strictly prohibited.
"""



# gunicorn.conf.py

import multiprocessing

# Bind to the development server's IP and port
bind = "0.0.0.0:8000"

# Number of worker processes: (2 * CPUs) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Threads per worker: For handling concurrent requests
threads = 2

# Timeout for worker processes (in seconds)
timeout = 120

# Log levels: 'debug', 'info', 'warning', 'error', 'critical'
loglevel = "info"

# Log files: Output logs to console or files for debugging
errorlog = "-"  # "-" means log to stderr
accesslog = "-"  # "-" means log to stdout
#errorlog = "/var/log/gunicorn/error.log"
#accesslog = "/var/log/gunicorn/access.log"

# Disable reload the application on code changes (for production)
reload = False

# PID file (useful for managing Gunicorn processes)
pidfile = "/tmp/gunicorn.pid"

# Disable detailed stack traces in error logs (for production development only)
capture_output = False

# Security: Avoid daemonizing for better process management during development
daemon = False
