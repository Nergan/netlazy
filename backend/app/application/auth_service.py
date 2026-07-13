import logging
import time
from datetime import datetime, timezone
from app.domain.models import User, UserAlreadyExistsError
from app.domain.repository import NonceRepository, UserRepository
from app.infrastructure import crypto_adapter

TIMESTAMP_TOLERANCE_SECONDS = 120

class InvalidPublicKeyError(Exception):
    """Raised when a submitted public key fails format or strength validation."""
    pass

class AuthenticationError(Exception):
    """Raised for any per-request signature authentication failure. Deliberately
    generic — callers should map this to a single opaque 401 to avoid leaking
    which check failed (timestamp vs unknown user vs bad signature vs replay)."""
    pass

class AuthService:
    def __init__(self, user_repo: UserRepository, nonce_repo: NonceRepository):
        self._user_repo = user_repo
        self._nonce_repo = nonce_repo

    async def register_user(self, public_key_pem: str) -> User:
        try:
            user_id = crypto_adapter.derive_user_id(public_key_pem)
        except crypto_adapter.InvalidPublicKeyError as e:
            raise InvalidPublicKeyError(str(e)) from e

        user = User(
            user_id=user_id,
            public_key_pem=public_key_pem,
            created_at=datetime.now(timezone.utc),
        )
        await self._user_repo.create(user)  # raises UserAlreadyExistsError on duplicate
        return user

    async def authenticate_request(
        self,
        user_id: str,
        timestamp: int,
        nonce: str,
        signature: bytes,
        canonical_payload: bytes,
    ) -> User:
        current_time = int(time.time())
        if abs(current_time - timestamp) > TIMESTAMP_TOLERANCE_SECONDS:
            logging.warning(f"Timestamp out of window for {user_id}")
            raise AuthenticationError("Timestamp out of tolerance window")

        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise AuthenticationError("Unknown user")

        try:
            crypto_adapter.verify_signature(user.public_key_pem, canonical_payload, signature)
        except crypto_adapter.SignatureVerificationError:
            logging.warning(f"Signature mismatch for user {user_id}")
            raise AuthenticationError("Signature verification failed")

        is_fresh = await self._nonce_repo.insert_if_not_exists(user_id, nonce)
        if not is_fresh:
            logging.warning(f"Replay attack blocked for user {user_id} with nonce {nonce}")
            raise AuthenticationError("Nonce already used")

        return user