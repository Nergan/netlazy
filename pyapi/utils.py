import time
import uuid
import hashlib
import base64
from typing import Optional, Dict
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def generate_keypair() -> tuple[str, str]:
    """Генерирует пару ключей Ed25519 и возвращает (private_pem, public_pem)."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    return private_pem, public_pem

def compute_next_nonce(previous_nonce: str) -> str:
    """Вычисляет следующий nonce как SHA256 от предыдущего."""
    return hashlib.sha256(previous_nonce.encode()).hexdigest()

def generate_initial_nonce() -> str:
    """Генерирует случайный начальный nonce (например, UUID)."""
    return uuid.uuid4().hex

def sign_request(
    method: str,
    path: str,
    body: Optional[bytes],
    private_key_pem: str,
    login: str,
    timestamp: str,
    nonce: str
) -> Dict[str, str]:
    """
    Формирует заголовки подписи.
    Возвращает словарь с заголовками X-Login, X-Timestamp, X-Nonce, X-Body-Hash, X-Signature.
    """
    # Если тело отсутствует, используем пустые байты
    body_bytes = body if body is not None else b''
    body_hash = hashlib.sha256(body_bytes).hexdigest()

    canonical = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    signature = private_key.sign(canonical.encode())
    signature_b64 = base64.b64encode(signature).decode()
    return {
        "X-Login": login,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Body-Hash": body_hash,
        "X-Signature": signature_b64,
    }