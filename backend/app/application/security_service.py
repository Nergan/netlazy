import hashlib
import uuid
import logging
from typing import Optional
from app.domain.models import PoWChallenge
from app.domain.repository import SecurityRepository, UserRepository

class BannedError(Exception):
    """Raised when IP, Fingerprint, or User ID is found in the cascade ban list."""
    pass

class ProofOfWorkError(Exception):
    """Raised when the Proof of Work challenge fails verification."""
    pass

class SecurityService:
    def __init__(self, security_repo: SecurityRepository, user_repo: UserRepository, difficulty: int):
        self._security_repo = security_repo
        self._user_repo = user_repo
        self._difficulty = difficulty

    async def generate_challenge(self) -> dict:
        """Creates a Proof of Work challenge and stores it for verification."""
        challenge = PoWChallenge(id=uuid.uuid4().hex, difficulty=self._difficulty)
        await self._security_repo.create_challenge(challenge)
        return {
            "challenge_id": challenge.id,
            "difficulty": challenge.difficulty
        }

    async def verify_pow(self, challenge_id: str, nonce: str) -> None:
        """
        Consumes a PoW challenge atomically.
        Calculates SHA256(challenge_id + nonce) and verifies it starts with `difficulty` zeros.
        """
        challenge = await self._security_repo.consume_challenge(challenge_id)
        if not challenge:
            raise ProofOfWorkError("Challenge expired, invalid, or already consumed.")
        
        target_prefix = "0" * challenge.difficulty
        payload = (challenge.id + nonce).encode('utf-8')
        result_hash = hashlib.sha256(payload).hexdigest()
        
        if not result_hash.startswith(target_prefix):
            logging.warning(f"PoW failure. Expected prefix {target_prefix}, got {result_hash[:challenge.difficulty]}")
            raise ProofOfWorkError("Invalid Proof of Work solution.")

    async def verify_not_banned(self, ip: str, fingerprint: str, user_id: Optional[str] = None) -> None:
        """Checks cascade ban lists. Raises BannedError if matched."""
        if await self._security_repo.is_banned(ip, fingerprint, user_id):
            raise BannedError("Access denied by security policy.")

    async def cascade_ban_user(self, user_id: str) -> None:
        """
        Administrative action: extracts all known footprint vectors (IPs and Fingerprints) 
        from the user's history and permanently blocks them globally.
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
            
        await self._security_repo.apply_bans(
            ips=user.known_ips,
            fingerprints=user.known_fingerprints,
            user_id=user.user_id
        )
        logging.info(f"Cascade ban applied for {user_id}. Blocked {len(user.known_ips)} IPs and {len(user.known_fingerprints)} fingerprints.")