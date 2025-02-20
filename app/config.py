import arrow
import time
from decouple import config
from pathlib import Path

# Paths
HOME = Path.home()
CWD = Path.cwd()

# Environment variables
JSON_FN = config("JSON_FN", default="raw/output.json")
TZ = config("TZ", default="America/Chicago")
BYPASS_SCHEDULE = config("OVERRIDE", default=False, cast=bool)

# Time settings
time.tzset()
CURRENT_TIME_LOCAL = arrow.now(TZ)
CURRENT_TIME_UTC = arrow.utcnow()
CURRENT_DAY = CURRENT_TIME_LOCAL.format("dddd")  # Monday, Tuesday, etc.

# Authentication settings
TTL = config("TTL", default=3600, cast=int)
HOST = config("HOST")
PORT = config("PORT", default=3000, cast=int)
SECRET_KEY = config("SECRET_KEY")
ALGORITHM = config("ALGORITHM", default="HS256")
TOKEN_EXPIRE = config("TOKEN_EXPIRE", default=30, cast=int)
COOKIE_NAME = "session_token"  # Name of the cookie that will store the session token
IS_DEV = HOST in ["localhost", "127.0.0.1", "0.0.0.0"] or PORT == 3000  # Development mode check

# Database settings
DB_NAME = config("DB_NAME")
DB_USER = config("DB_USER")
DB_PASS = config("DB_PASS")
DB_HOST = config("DB_HOST")
DB_PORT = config("DB_PORT", default=5432, cast=int)

# CORS settings
ORIGINS = [
    "http://localhost",
    f"http://localhost:{PORT}",
    "http://127.0.0.1",
    f"http://127.0.0.1:{PORT}",
    "http://0.0.0.0",
    f"http://0.0.0.0:{PORT}",
]

# Logging prefixes
INFO = "INFO:"
ERROR = "ERROR:"
WARNING = "WARNING:"
