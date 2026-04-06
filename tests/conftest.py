import os
import sys
import time
import hashlib
import base64
from pathlib import Path
from typing import Tuple
import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Добавляем папку server в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

# Переопределяем имя БД для тестов и отключаем rate limit
os.environ["DATABASE_NAME"] = "netlazy_test"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"  # высокий лимит, чтобы не мешал

from main import app
from core.deps import _nonce_cache
from core.rate_limit import RateLimitMiddleware
from core.config import get_settings

# Синхронная очистка БД через pymongo (только если нужно)
from pymongo import MongoClient


@pytest.fixture(scope="session")
def client():
    """Тестовый клиент. FastAPI сам управляет lifespan и event loop."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_state(client):
    """Очищает in-memory кеши и коллекцию users перед каждым тестом."""
    # Очищаем кеш nonce
    _nonce_cache.clear()
    # Очищаем кеш rate limiter
    for middleware in app.user_middleware:
        if middleware.cls == RateLimitMiddleware and hasattr(middleware, 'requests'):
            middleware.requests.clear()
    
    # Очищаем коллекцию users через синхронное подключение
    settings = get_settings()
    sync_client = MongoClient(settings.mongodb_uri)
    db = sync_client[settings.database_name]
    db.users.delete_many({})
    sync_client.close()


# === Вспомогательные функции для генерации ключей и подписи ===
def generate_ed25519_keypair() -> Tuple[str, str]:
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    return public_pem, private_pem


def sign_request(private_key_pem: str, method: str, path: str, timestamp: int,
                 nonce: str, body: bytes) -> str:
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    signature = private_key.sign(canonical.encode())
    return base64.b64encode(signature).decode()


def make_signed_request(client, method: str, path: str, login: str,
                        private_key_pem: str, body: dict = None,
                        extra_headers: dict = None):
    import json
    # Сериализуем без лишних пробелов
    body_bytes = json.dumps(body, separators=(',', ':')).encode() if body else b''
    timestamp = int(time.time())
    nonce = f"test_{timestamp}_{hash(body_bytes) % 10000}"
    signature = sign_request(private_key_pem, method, path, timestamp, nonce, body_bytes)
    headers = {
        "X-Login": login,
        "X-Timestamp": str(timestamp),
        "X-Nonce": nonce,
        "X-Body-Hash": hashlib.sha256(body_bytes).hexdigest(),
        "X-Signature": signature,
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    # Используем content=body_bytes, чтобы точно отправить наши байты
    return client.request(method, path, content=body_bytes, headers=headers)


@pytest.fixture
def user_alice(client):
    """Регистрирует пользователя alice и возвращает его данные."""
    public_key, private_key = generate_ed25519_keypair()
    resp = client.post("/auth/register", json={
        "login": "alice",
        "public_key": public_key,
        "key_algorithm": "Ed25519"
    })
    assert resp.status_code == 200
    return {"login": "alice", "private_key": private_key, "public_key": public_key}