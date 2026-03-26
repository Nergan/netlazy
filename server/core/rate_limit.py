import time
from collections import OrderedDict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import settings

RATE_LIMIT = settings.rate_limit_per_minute
RATE_LIMIT_WINDOW = settings.rate_limit_window_seconds
CACHE_SIZE = settings.rate_limit_cache_size


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests = OrderedDict()  # IP -> список временных меток

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next):
        client_ip = self._get_client_ip(request)
        now = time.time()

        # Очистка устаревших записей для всех IP (ограничимся очисткой только при превышении кэша)
        # Для этого при каждом запросе проходимся по всем ключам – может быть дорого.
        # Вместо этого будем очищать только для текущего IP, а глобальную очистку делать раз в N запросов.
        # Для простоты оставим локальную очистку и при достижении лимита удалим самые старые IP.

        # Получаем список меток для этого IP
        timestamps = self.requests.get(client_ip, [])
        # Оставляем только метки в окне
        timestamps = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW]

        if len(timestamps) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        timestamps.append(now)
        self.requests[client_ip] = timestamps

        # Ограничиваем размер кэша (LRU)
        # Если кэш переполнен, удаляем самый старый ключ (без учёта активности)
        if len(self.requests) > CACHE_SIZE:
            # Удаляем самый старый ключ (первый в OrderedDict)
            self.requests.popitem(last=False)

        response = await call_next(request)
        return response