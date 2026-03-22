import time
import base64
from typing import Optional
from fastapi import Request, HTTPException, Depends
from core.database import get_users_collection
from services.crypto import verify_signature
import redis.asyncio as redis
from core.config import settings

# Настройки
SIGNATURE_EXPIRY = 300  # 5 минут

# Redis клиент (если указан в конфиге)
redis_client = None
if settings.redis_url:
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    except:
        redis_client = None

async def get_current_user(request: Request, required: bool = True) -> Optional[str]:
    """
    Извлекает и проверяет подпись запроса.
    Возвращает логин пользователя при успехе.
    Если required=True и подпись отсутствует/неверна -> 401.
    Если required=False и заголовки не переданы -> None.
    """
    headers = request.headers
    login = headers.get("x-login")
    timestamp_str = headers.get("x-timestamp")
    nonce = headers.get("x-nonce")
    signature_b64 = headers.get("x-signature")

    # Если заголовков нет, а required=False -> возвращаем None
    if not any([login, timestamp_str, nonce, signature_b64]):
        if required:
            raise HTTPException(status_code=401, detail="Missing signature headers")
        return None

    # Если есть хотя бы один заголовок, должны быть все
    if not all([login, timestamp_str, nonce, signature_b64]):
        raise HTTPException(status_code=401, detail="Incomplete signature headers")

    # Проверка timestamp
    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp")

    now = int(time.time())
    if abs(now - timestamp) > SIGNATURE_EXPIRY:
        raise HTTPException(status_code=401, detail="Timestamp expired")

    # Проверка nonce (защита от повторов)
    if redis_client:
        key = f"nonce:{login}:{nonce}"
        exists = await redis_client.get(key)
        if exists:
            raise HTTPException(status_code=401, detail="Nonce already used")
        await redis_client.setex(key, SIGNATURE_EXPIRY, timestamp)
    else:
        # fallback in-memory (только для разработки)
        from collections import OrderedDict
        if not hasattr(request.app.state, "nonce_cache"):
            request.app.state.nonce_cache = OrderedDict()
        cache_key = f"{login}:{nonce}"
        if cache_key in request.app.state.nonce_cache:
            raise HTTPException(status_code=401, detail="Nonce already used")
        request.app.state.nonce_cache[cache_key] = now
        # очистка устаревших (можно добавить позже)

    # Получение публичного ключа пользователя
    users_collection = await get_users_collection()
    user = await users_collection.find_one({"public.id": login})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    public_key_pem = user["private"]["public_key"]
    algorithm = user["private"].get("key_algorithm", "Ed25519")

    # Формирование канонической строки для подписи
    method = request.method
    path = request.url.path
    # Внимание: тело запроса ещё не прочитано, поэтому мы не можем его включить.
    # Вместо этого клиент должен передавать хэш тела в заголовке X-Body-Hash.
    body_hash = headers.get("x-body-hash") or ""
    canonical = f"{method}\n{path}\n{timestamp_str}\n{nonce}\n{body_hash}"

    # Проверка подписи
    try:
        valid = await verify_signature(public_key_pem, canonical.encode(), signature_b64, algorithm)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Signature verification error: {str(e)}")

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Всё хорошо, сохраняем полезные данные в request.state
    request.state.login = login
    request.state.body_hash = body_hash
    
    # Обновляем last_online (асинхронно, не ждём)
    await users_collection.update_one(
        {"public.id": login},
        {"$set": {"private.last_online": int(time.time())}}
    )
    
    return login


# Вспомогательные зависимости
async def current_user_required(request: Request) -> str:
    user = await get_current_user(request, required=True)
    return user  # гарантированно строка

async def current_user_optional(request: Request) -> Optional[str]:
    return await get_current_user(request, required=False)