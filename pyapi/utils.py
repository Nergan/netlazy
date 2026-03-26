import hashlib
import base64
from typing import Optional, Dict
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


def generate_keypair() -> tuple[str, str]:
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
    return hashlib.sha256(previous_nonce.encode()).hexdigest()


def generate_initial_nonce() -> str:
    import uuid
    return uuid.uuid4().hex


def sign_request(
    method: str,
    full_path: str,          # включает query, например "/users/list?tags=it&limit=20"
    body: Optional[bytes],
    private_key_pem: str,
    login: str,
    timestamp: str,
    nonce: str
) -> Dict[str, str]:
    body_bytes = body if body is not None else b''
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    canonical = f"{method}\n{full_path}\n{timestamp}\n{nonce}\n{body_hash}"
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