import base64
import hashlib
import pytest
from services.crypto import verify_signature
from conftest import generate_ed25519_keypair, sign_request


@pytest.mark.asyncio
async def test_verify_signature_valid():
    pub, priv = generate_ed25519_keypair()
    message = b"test message"
    timestamp = 123456
    nonce = "abc"
    body_hash = hashlib.sha256(b"{}").hexdigest()
    canonical = f"GET\n/users/me\n{timestamp}\n{nonce}\n{body_hash}"
    signature = sign_request(priv, "GET", "/users/me", timestamp, nonce, b"{}")
    valid = await verify_signature(pub, canonical.encode(), signature)
    assert valid is True


@pytest.mark.asyncio
async def test_verify_signature_invalid():
    pub, _ = generate_ed25519_keypair()
    signature = base64.b64encode(b"fake").decode()
    valid = await verify_signature(pub, b"anything", signature)
    assert valid is False