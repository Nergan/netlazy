from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from app.domain.models import Handshake, Profile, Tag, User

class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> None:
        ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        ...

class NonceRepository(ABC):
    @abstractmethod
    async def insert_if_not_exists(self, user_id: str, nonce: str) -> bool:
        ...

class TagRepository(ABC):
    @abstractmethod
    async def sync(self, tags: List[Tag]) -> None:
        ...

    @abstractmethod
    async def list_visible(self) -> List[Tag]:
        ...

    @abstractmethod
    async def search(self, query: str) -> List[Tag]:
        ...

    @abstractmethod
    async def get_all_names(self) -> List[str]:
        ...

class ProfileRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[Profile]:
        ...
        
    @abstractmethod
    async def get_by_user_ids(self, user_ids: List[str]) -> List[Profile]:
        ...

    @abstractmethod
    async def upsert(self, profile: Profile) -> None:
        ...
        
    @abstractmethod
    async def get_feed(self, viewer_id: str, exclude_ids: List[str], cursor: datetime, requires: List[str], excludes: List[str], limit: int) -> List[Profile]:
        """Fetches a paginated batch of profiles matching requirements."""
        ...

class HandshakeRepository(ABC):
    @abstractmethod
    async def create(self, handshake: Handshake) -> None:
        ...

    @abstractmethod
    async def update(self, handshake: Handshake) -> None:
        ...

    @abstractmethod
    async def get_by_id(self, handshake_id: str) -> Optional[Handshake]:
        ...

    @abstractmethod
    async def get_for_user(self, user_id: str) -> List[Handshake]:
        ...

    @abstractmethod
    async def get_interacted_user_ids(self, user_id: str) -> List[str]:
        ...

class MediaStorage(ABC):
    @abstractmethod
    async def upload(self, file_bytes: bytes, media_type: str, public_id_hint: str) -> str:
        ...