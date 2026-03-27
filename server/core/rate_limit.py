import time
from collections import OrderedDict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from core.config import get_settings

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests = OrderedDict()

    def _get_client_ip(self, request: Request) -> str:
        # Используем только реальный IP, игнорируем прокси-заголовки
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        client_ip = self._get_client_ip(request)
        now = time.time()

        timestamps = self.requests.get(client_ip, [])
        timestamps = [ts for ts in timestamps if now - ts < settings.rate_limit_window_seconds]

        if len(timestamps) >= settings.rate_limit_per_minute:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        timestamps.append(now)
        self.requests[client_ip] = timestamps
        self.requests.move_to_end(client_ip)

        if len(self.requests) > settings.rate_limit_cache_size:
            self.requests.popitem(last=False)

        response = await call_next(request)
        return response