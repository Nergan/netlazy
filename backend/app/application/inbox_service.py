import uuid
from datetime import datetime, timezone
from typing import List, Tuple
from app.domain.models import Handshake, Profile
from app.domain.repository import HandshakeRepository, ProfileRepository

class HandshakeNotFoundError(Exception): pass
class InvalidHandshakeStateError(Exception): pass
class UnauthorizedHandshakeActionError(Exception): pass
class OtherUserNotFoundError(Exception): pass
class OtherUserBannedError(Exception): pass

class InboxService:
    def __init__(self, handshake_repo: HandshakeRepository, profile_repo: ProfileRepository):
        self._handshake_repo = handshake_repo
        self._profile_repo = profile_repo

    async def send_handshake(self, sender_id: str, receiver_id: str, handshake_type: str, offered_contact: str = None) -> Handshake:
        existing = await self._handshake_repo.get_between_users(sender_id, receiver_id)
        if existing:
            existing.sender_id = sender_id
            existing.receiver_id = receiver_id
            existing.handshake_type = handshake_type
            existing.status = "pending"
            existing.offered_contact = offered_contact
            existing.returned_contact = None
            existing.sender_deleted = False
            existing.receiver_deleted = False
            existing.updated_at = datetime.now(timezone.utc)
            await self._handshake_repo.update(existing)
            return existing
        else:
            h = Handshake(
                id=uuid.uuid4().hex,
                sender_id=sender_id,
                receiver_id=receiver_id,
                handshake_type=handshake_type,
                status="pending",
                offered_contact=offered_contact,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            await self._handshake_repo.create(h)
            return h

    async def resolve_handshake(self, user_id: str, handshake_id: str, status: str, returned_contact: str = None) -> Handshake:
        h = await self._handshake_repo.get_by_id(handshake_id)
        if not h:
            raise HandshakeNotFoundError("Handshake not found")
        if h.receiver_id != user_id:
            raise UnauthorizedHandshakeActionError("Only the receiver can resolve this handshake")
        if h.status != "pending":
            raise InvalidHandshakeStateError(f"Handshake is already {h.status}")

        other_id = h.sender_id if h.receiver_id == user_id else h.receiver_id
        from app.database import db_instance
        other_user = await db_instance.users_collection.find_one({"user_id": other_id})
        if not other_user:
            raise OtherUserNotFoundError("user account has been deleted")
        if other_user.get("is_banned"):
            raise OtherUserBannedError("user account has been banned")

        h.status = status
        if status == "accepted" and returned_contact:
            h.returned_contact = returned_contact
            
        if status == "declined":
            h.receiver_deleted = True
            
        h.updated_at = datetime.now(timezone.utc)

        await self._handshake_repo.update(h)
        return h

    async def get_inbox(self, user_id: str) -> List[Tuple[Handshake, Profile]]:
        handshakes = await self._handshake_repo.get_for_user(user_id)
        if not handshakes:
            return []

        other_user_ids = {h.sender_id if h.receiver_id == user_id else h.receiver_id for h in handshakes}

        from app.database import db_instance
        active_users_cursor = db_instance.users_collection.find({
            "user_id": {"$in": list(other_user_ids)},
            "is_banned": {"$ne": True}
        })
        active_user_ids = {u["user_id"] async for u in active_users_cursor}

        profiles = await self._profile_repo.get_by_user_ids(list(other_user_ids))
        profile_map = {p.user_id: p for p in profiles}

        result = []
        for h in handshakes:
            other_id = h.sender_id if h.receiver_id == user_id else h.receiver_id
            if other_id not in active_user_ids:
                continue

            profile = profile_map.get(other_id) or Profile(user_id=other_id)
            result.append((h, profile))

        return result

    async def delete_user_handshakes(self, user_id: str) -> None:
        await self._handshake_repo.delete_for_user(user_id)