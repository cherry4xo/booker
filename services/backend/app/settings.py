import os
import random
import string
from dotenv import load_dotenv
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DB_URL = f"postgres://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

DB_CONNECTIONS = {
        "default": DB_URL,
    }

SECRET_KEY = os.getenv("SECRET_KEY", default="".join([random.choice(string.ascii_letters) for _ in range(32)]))
CLIENT_ID = os.getenv("CLIENT_ID", default="".join([random.choice(string.ascii_letters) for _ in range(32)]))

CORS_ORIGINS = ["*"]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]

DEFAULT_MODERATOR_USERNAME = os.getenv("DEFAULT_MODERATOR_USERNAME", default="moderator")
DEFAULT_MODERATOR_EMAIL = os.getenv("DEFAULT_MODERATOR_EMAIL", default="moderator@example.com")
DEFAULT_MODERATOR_PASSWORD = os.getenv("DEFAULT_MODERATOR_PASSWORD", default="password")

LOGIN_URL = LOGIN_URL = f"http://auth:8080/login/access-token"