import logging
from logging.handlers import RotatingFileHandler
import os

from app import settings

LOG_FILE = "logs/service.log"
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5


def setup_logging(service_name: str):
    # Корневой логгер
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    if settings.MODE == "DEBUG":
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logger = logging.getLogger()
    logger.setLevel(log_level)
    if logger.hasHandlers():
        logger.handlers.clear()

    fmt = logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s'
    )

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # Консоль
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    logger.info(f"Logging initialized for {service_name}")
    return logger


from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger = logging.getLogger("access")
        logger.info(f"--> {request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"<-- {request.method} {request.url} - {response.status_code}")
        return response
    

import functools

def log_calls(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.info(f"Calling {func.__name__} args={args} kwargs={kwargs}")
        result = await func(*args, **kwargs)
        logger.info(f"{func.__name__} returned {result}")
        return result
    return wrapper