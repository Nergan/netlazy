import time
import uuid
import hashlib
import base64
from typing import Dict
from cryptography.hazmat.primitives.asymmetric import ed25519

def sign_request(
    method: str,
    path: str,
    body: bytes,
    private_key: ed25519.Ed25519PrivateKey,
    login: str
) -> Dict[str, str]:
    """
    Формирует заголовки для подписанного запроса.
    body должен быть байтовой строкой (или None).
    """
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    body_hash = hashlib.sha256(body).hexdigest() if body else ""
    canonical = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    signature = private_key.sign(canonical.encode())
    signature_b64 = base64.b64encode(signature).decode()
    return {
        "X-Login": login,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Body-Hash": body_hash,
        "X-Signature": signature_b64,
    }