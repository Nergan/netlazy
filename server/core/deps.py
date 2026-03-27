import time
import hashlib
import asyncio
from typing import Optional
from collections import OrderedDict
from urllib.parse import parse_qs, urlencode
from fastapi import Request, HTTPException
from core.database import get_users_collection
from services.crypto import verify_signature
from core.config import get_settings

SIGNATURE_EXPIRY = 300

_nonce_cache = OrderedDict()
_nonce_lock = asyncio.Lock()

def _clean_nonce_cache():
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

    if not any([login, timestamp_str, nonce, signature_b64, body_hash_header]):
        if required:
            raise HTTPException(status_code=401, detail="Missing authentication headers")
        return None

    if not all([login, timestamp_str, nonce, signature_b64, body_hash_header]):
        raise HTTPException(status_code=401, detail="Incomplete authentication headers")

    if nonce and len(nonce) > 128:
        raise HTTPException(status_code=400, detail="Nonce too long")

    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp")

    now = int(time.time())
    if abs(now - timestamp) > SIGNATURE_EXPIRY:
        raise HTTPException(status_code=401, detail="Timestamp expired")

    body = request.state.body
    body_hash = hashlib.sha256(body).hexdigest()
    if body_hash != body_hash_header:
        raise HTTPException(status_code=400, detail="Body hash mismatch")

    users_collection = await get_users_collection()
    user = await users_collection.find_one(
        {"public.id": login},
        {"private.public_key": 1, "private.key_algorithm": 1, "_id": 0}
    )
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    public_key_pem = user["private"]["public_key"]
    algorithm = user["private"].get("key_algorithm", "Ed25519")

    method = request.method
    path = request.url.path
    query_dict = parse_qs(request.url.query, keep_blank_values=True)
    sorted_items = sorted(query_dict.items())
    normalized_query = urlencode(sorted_items, doseq=True) if sorted_items else ""
    full_path = path + (f"?{normalized_query}" if normalized_query else "")

    canonical = f"{method}\n{full_path}\n{timestamp_str}\n{nonce}\n{body_hash}"

    try:
        valid = await verify_signature(public_key_pem, canonical.encode(), signature_b64, algorithm)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Signature verification error: {str(e)}")

    if not valid:
        raise HTTPException(status_code=401, detail="Invalid signature")

    settings = get_settings()
    cache_key = f"{login}:{nonce}"
    async with _nonce_lock:
        _clean_nonce_cache()
        if cache_key in _nonce_cache:
            raise HTTPException(status_code=409, detail="Nonce already used")
        _nonce_cache[cache_key] = time.time() + SIGNATURE_EXPIRY
        if len(_nonce_cache) > settings.nonce_cache_max_size:
            _nonce_cache.popitem(last=False)

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