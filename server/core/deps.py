import time
import base64
from typing import Optional
from fastapi import Request, HTTPException, Depends
from core.database import get_users_collection
from services.crypto import verify_signature
from core.config import settings
import hashlib

# Настройки
SIGNATURE_EXPIRY = 300  # 5 минут
        

async def get_current_user(request: Request, required: bool = True) -> Optional[str]:   
    headers = request.headers
    login = headers.get("x-login")
    timestamp_str = headers.get("x-timestamp")
    nonce = headers.get("x-nonce")
    signature_b64 = headers.get("x-signature")

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

    users_collection = await get_users_collection()
    user = await users_collection.find_one({"public.id": login})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    public_key_pem = user["private"]["public_key"]
    algorithm = user["private"].get("key_algorithm", "Ed25519")

    # Формирование канонической строки (body_hash берём из заголовка)
    method = request.method
    path = request.url.path
    body_hash = headers.get("x-body-hash") or ""
    canonical = f"{method}\n{path}\n{timestamp_str}\n{nonce}\n{body_hash}"

    # Проверка подписи
    try:
        valid = await verify_signature(public_key_pem, canonical.encode(), signature_b64, algorithm)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Signature verification error: {str(e)}")

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid signature")

    # ---------- Проверка и обновление nonce (цепочка) ----------
    last_nonce = user["private"].get("last_nonce")

    if last_nonce is None:
        # Первый запрос после регистрации – сохраняем переданный nonce
        new_nonce = nonce
    else:
        # Ожидаем, что nonce = hash(last_nonce)
        expected = hashlib.sha256(last_nonce.encode()).hexdigest()
        if nonce != expected:
            raise HTTPException(status_code=401, detail="Invalid nonce chain")
        new_nonce = nonce

    # Атомарное обновление (гарантирует, что nonce не изменился конкурентно)
    result = await users_collection.find_one_and_update(
        {"public.id": login, "private.last_nonce": last_nonce},
        {"$set": {"private.last_nonce": new_nonce, "private.last_online": now}},
        projection={"_id": 0},
        return_document=False
    )
    if result is None:
        # Конфликт: кто-то другой уже обновил nonce
        raise HTTPException(status_code=409, detail="Nonce conflict, please retry")

    # Сохраняем логин в request.state для использования в обработчиках
    request.state.login = login
    request.state.body_hash = body_hash
    return login


async def current_user_required(request: Request) -> str:
    return await get_current_user(request, required=True)

async def current_user_optional(request: Request) -> Optional[str]:
    return await get_current_user(request, required=False)