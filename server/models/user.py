from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
import re

class LocationPrecise(BaseModel):
    type: str = "Point"
    coordinates: List[float]

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

    @field_validator('dob')
    @classmethod
    def validate_dob(cls, v):
        if v and not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError('dob must be YYYY-MM-DD')
        return v

    @field_validator('img')
    @classmethod
    def validate_img_size(cls, v):
        if v and len(v) > 7_000_000:
            raise ValueError('image too large, max 5MB')
        return v

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
    last_nonce: Optional[str] = None

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
    def validate_img_size(cls, v):
        if v and len(v) > 7_000_000:
            raise ValueError('image too large, max 5MB')
        return v
