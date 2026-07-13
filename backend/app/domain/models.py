from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

@dataclass
class User:
    user_id: str
    public_key_pem: str
    created_at: datetime

class UserAlreadyExistsError(Exception):
    """Raised when attempting to register a public key that is already registered."""
    pass

@dataclass
class Tag:
    name: str
    category: str
    aliases: List[str] = field(default_factory=list)
    hidden: bool = False

@dataclass
class MediaItem:
    url: str
    media_type: str  # "image" | "video" | "audio"
    blur: bool = False

@dataclass
class Contact:
    type: str  # "email" | "link" | "phone" | "unknown"
    value: str
    is_private: bool = True

@dataclass
class Profile:
    user_id: str
    bio: str = ""
    tags: List[str] = field(default_factory=list)
    media: List[MediaItem] = field(default_factory=list)
    audio: Optional[MediaItem] = None
    contacts: List[Contact] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

@dataclass
class Handshake:
    id: str
    sender_id: str
    receiver_id: str
    handshake_type: str  # "mutual", "demand", "share", "exchange"
    status: str  # "pending", "accepted", "declined"
    offered_contact: Optional[str] = None
    returned_contact: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None