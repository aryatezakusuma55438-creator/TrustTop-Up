import os
import sys

class Config:
    _secret = os.environ.get('SECRET_KEY', '')
    if not _secret:
        print("[ERROR] SECRET_KEY tidak ditemukan di .env!", file=sys.stderr)
        sys.exit(1)
    SECRET_KEY = _secret

    WTF_CSRF_ENABLED    = True
    WTF_CSRF_TIME_LIMIT = 3600
    PERMANENT_SESSION_LIFETIME = 7200

    DATABASE      = os.path.join(os.path.dirname(__file__), 'database.db')
    ADMIN_USER    = os.environ.get('ADMIN_USER', '')
    ADMIN_PASS    = os.environ.get('ADMIN_PASS', '')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024

    # Midtrans
    MIDTRANS_SERVER_KEY    = os.environ.get('MIDTRANS_SERVER_KEY', '')
    MIDTRANS_CLIENT_KEY    = os.environ.get('MIDTRANS_CLIENT_KEY', '')
    MIDTRANS_IS_PRODUCTION = os.environ.get('MIDTRANS_IS_PRODUCTION', 'False').lower() == 'true'
