import logging
import time
from datetime import datetime, timezone
from app.domain.models import User, UserAlreadyExistsError
from app.domain.repository import NonceRepository, UserRepository, ProfileRepository, HandshakeRepository
from app.infrastructure import crypto_adapter

TIMESTAMP_TOLERANCE_SECONDS = 120

class InvalidPublicKeyError(Exception):
    """Raised when a submitted public key fails format or strength validation."""
    pass

class AuthenticationError(Exception):
    """Raised for any per-request signature authentication failure."""
    pass

class AuthService:
    def __init__(self, user_repo: UserRepository, nonce_repo: NonceRepository):
        self._user_repo = user_repo
        self._nonce_repo = nonce_repo

    async def register_user(self, public_key_pem: str, ip: str = None, fingerprint: str = None) -> User:
        try:
            user_id = crypto_adapter.derive_user_id(public_key_pem)
        except crypto_adapter.InvalidPublicKeyError as e:
            raise InvalidPublicKeyError(str(e)) from e

        user = User(
            user_id=user_id,
            public_key_pem=public_key_pem,
            created_at=datetime.now(timezone.utc),
            known_ips=[ip] if ip else [],
            known_fingerprints=[fingerprint] if fingerprint else []
        )
        await self._user_repo.create(user) 
        return user

    async def rotate_key(
        self,
        old_user_id: str,
        new_public_key_pem: str,
        profile_repo: ProfileRepository,
        handshake_repo: HandshakeRepository
    ) -> str:
        """
        Secures identity key regeneration on the backend:
        Creates a new User ID, migrates existing Profile details seamlessly to avoid CDN drops,
        deletes old handshakes and old user credentials atomically.
        """
        try:
            new_user_id = crypto_adapter.derive_user_id(new_public_key_pem)
        except crypto_adapter.InvalidPublicKeyError as e:
            raise InvalidPublicKeyError(str(e)) from e

        from app.database import db_instance

        async def _transaction_callback(session):
            existing_user = await self._user_repo.get_by_id(new_user_id, session=session)
            if existing_user:
                raise UserAlreadyExistsError("New public key already registered")

            old_user = await self._user_repo.get_by_id(old_user_id, session=session)
            known_ips = old_user.known_ips if old_user else []
            known_fingerprints = old_user.known_fingerprints if old_user else []

            new_user = User(
                user_id=new_user_id,
                public_key_pem=new_public_key_pem,
                created_at=datetime.now(timezone.utc),
                known_ips=known_ips,
                known_fingerprints=known_fingerprints
            )
            await self._user_repo.create(new_user, session=session)

            old_profile = await profile_repo.get_by_user_id(old_user_id, session=session)
            if old_profile:
                old_profile.user_id = new_user_id
                old_profile.updated_at = datetime.now(timezone.utc)
                await profile_repo.upsert(old_profile, session=session)
                await profile_repo.delete(old_user_id, session=session)

            await handshake_repo.delete_for_user(old_user_id, session=session)
            await self._nonce_repo.delete_for_user(old_user_id, session=session)
            await self._user_repo.delete(old_user_id, session=session)

            return new_user_id

        # Motor start_session() returns an async context manager, so it needs to be awaited before `async with`
        async with await db_instance.client.start_session() as session:
            return await session.with_transaction(_transaction_callback)

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

    async def delete_user(self, user_id: str) -> None:
        await self._user_repo.delete(user_id)
        await self._nonce_repo.delete_for_user(user_id)