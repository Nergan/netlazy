from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
import re
import base64

class LocationPrecise(BaseModel):
    type: str = "Point"
    coordinates: List[float]

    @field_validator('coordinates')
    @classmethod
    def validate_coordinates(cls, v):
        if len(v) != 2:
            raise ValueError('coordinates must be [longitude, latitude]')
        lon, lat = v
        if not (-180 <= lon <= 180):
            raise ValueError('longitude must be between -180 and 180')
        if not (-90 <= lat <= 90):
            raise ValueError('latitude must be between -90 and 90')
        return v

class Location(BaseModel):
    precise: Optional[LocationPrecise] = None
    exemplary: Optional[List[str]] = None

class SexEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"

class UserPublic(BaseModel):
    id: str  # логин
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[SexEnum] = None
    desc: Optional[str] = None
    img: Optional[str] = None
    location: Optional[Location] = None
    tags: Optional[List[str]] = None

    @field_validator('id')
    @classmethod
    def validate_id(cls, v):
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('id must contain only lowercase letters, digits, and hyphens')
        return v

    @field_validator('dob')
    @classmethod
    def validate_dob(cls, v):
        if v and not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('dob must be YYYY-MM-DD')
        return v

    @field_validator('img')
    @classmethod
    def validate_img(cls, v):
        if v is None:
            return v
        try:
            img_data = base64.b64decode(v)
        except Exception:
            raise ValueError('invalid base64 image')
        # Проверка размера (5 МБ)
        if len(img_data) > 5 * 1024 * 1024:
            raise ValueError('image too large, max 5MB')
        # Проверка типа (JPEG или PNG)
        if img_data.startswith(b'\xff\xd8') or img_data.startswith(b'\x89PNG\r\n\x1a\n'):
            return v
        raise ValueError('unsupported image format, only JPEG and PNG allowed')

class ContactItem(BaseModel):
    is_public: bool
    contact: str

class UserProtect(BaseModel):
    contacts: Optional[List[ContactItem]] = Field(default_factory=list)
    is_online: bool = False

class UserPrivate(BaseModel):
    public_key: str                     # публичный ключ в формате PEM
    key_algorithm: str = "Ed25519"       # алгоритм подписи
    requests: List[dict] = Field(default_factory=list)
    created_at: int
    last_online: int
    last_nonce: Optional[str] = None     # поле больше не используется, но оставлено для совместимости

class UserInDB(BaseModel):
    public: UserPublic
    protect: UserProtect = Field(default_factory=UserProtect)
    private: UserPrivate

class UserPublicListResponse(BaseModel):
    items: List[UserPublic]
    total: int

class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[SexEnum] = None
    desc: Optional[str] = None
    img: Optional[str] = None
    location: Optional[Location] = None
    tags: Optional[List[str]] = None

    @field_validator('dob')
    @classmethod
    def validate_dob(cls, v):
        if v and not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('dob must be YYYY-MM-DD')
        return v

    @field_validator('img')
    @classmethod
    def validate_img(cls, v):
        if v is None:
            return v
        try:
            img_data = base64.b64decode(v)
        except Exception:
            raise ValueError('invalid base64 image')
        if len(img_data) > 5 * 1024 * 1024:
            raise ValueError('image too large, max 5MB')
        if img_data.startswith(b'\xff\xd8') or img_data.startswith(b'\x89PNG\r\n\x1a\n'):
            return v
        raise ValueError('unsupported image format, only JPEG and PNG allowed')