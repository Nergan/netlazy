import base64
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

async def verify_signature(public_key_pem: str, message: bytes, signature_b64: str, algorithm: str = "Ed25519") -> bool:
    """Проверяет подпись (асинхронная обёртка, но внутри синхронный код)."""
    try:
        signature = base64.b64decode(signature_b64)
    except:
        return False

    try:
        if algorithm == "Ed25519":
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                return False
            public_key.verify(signature, message)
            return True
        elif algorithm == "RSA":
            public_key = serialization.load_pem_public_key(public_key_pem.encode())
            if not isinstance(public_key, rsa.RSAPublicKey):
                return False
            public_key.verify(
                signature,
                message,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return True
        else:
            return False
    except InvalidSignature:
        return False
    except Exception:
        return False

def validate_public_key(public_key_pem: str, expected_algorithm: str) -> bool:
    """
    Проверяет, что переданный PEM-ключ соответствует ожидаемому алгоритму.
    Возвращает True, если ключ корректен и имеет нужный тип.
    """
    try:
        key = serialization.load_pem_public_key(public_key_pem.encode())
        if expected_algorithm == "Ed25519":
            return isinstance(key, ed25519.Ed25519PublicKey)
        elif expected_algorithm == "RSA":
            return isinstance(key, rsa.RSAPublicKey)
        else:
            return False
    except Exception:
        return False