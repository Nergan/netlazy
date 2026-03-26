import time
import hashlib
import asyncio
from typing import Optional
from fastapi import Request, HTTPException
from core.database import get_users_collection
from services.crypto import verify_signature

SIGNATURE_EXPIRY = 300  # 5 минут

# In‑memory кэш использованных nonce
_nonce_cache: dict[str, float] = {}
_nonce_lock = asyncio.Lock()


def _clean_nonce_cache():
    """Удаляет просроченные nonce."""
    now = time.time()
    expired = [k for k, t in _nonce_cache.items() if t < now]
    for k in expired:
        del _nonce_cache[k]


async def get_current_user(request: Request, required: bool = True) -> Optional[str]:
    headers = request.headers
    login = headers.get("x-login")
    timestamp_str = headers.get("x-timestamp")
    nonce = headers.get("x-nonce")
    signature_b64 = headers.get("x-signature")
    body_hash_header = headers.get("x-body-hash", "")

    if not any([login, timestamp_str, nonce, signature_b64]):
        if required:
            raise HTTPException(status_code=401, detail="Missing signature headers")
        return None

    if not all([login, timestamp_str, nonce, signature_b64]):
        raise HTTPException(status_code=401, detail="Incomplete signature headers")

    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp")

    now = int(time.time())
    if abs(now - timestamp) > SIGNATURE_EXPIRY:
        raise HTTPException(status_code=401, detail="Timestamp expired")

    # Используем сохранённое тело (middleware)
    body = request.state.body
    body_hash = hashlib.sha256(body).hexdigest()
    if body_hash != body_hash_header:
        raise HTTPException(status_code=400, detail="Body hash mismatch")

    # Получение пользователя и публичного ключа
    users_collection = await get_users_collection()
    user = await users_collection.find_one({"public.id": login})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    public_key_pem = user["private"]["public_key"]
    algorithm = user["private"].get("key_algorithm", "Ed25519")

    # Формирование канонической строки
    method = request.method
    path = request.url.path
    canonical = f"{method}\n{path}\n{timestamp_str}\n{nonce}\n{body_hash}"

    # Проверка подписи
    try:
        valid = await verify_signature(public_key_pem, canonical.encode(), signature_b64, algorithm)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Signature verification error: {str(e)}")

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Проверка nonce (replay‑attack)
    cache_key = f"{login}:{nonce}"
    async with _nonce_lock:
        _clean_nonce_cache()
        if cache_key in _nonce_cache:
            raise HTTPException(status_code=409, detail="Nonce already used")
        _nonce_cache[cache_key] = time.time() + SIGNATURE_EXPIRY

    # Обновляем last_online
    await users_collection.update_one(
        {"public.id": login},
        {"$set": {"private.last_online": now}}
    )

    request.state.login = login
    return login


async def current_user_required(request: Request) -> str:
    return await get_current_user(request, required=True)


async def current_user_optional(request: Request) -> Optional[str]:
    return await get_current_user(request, required=False)