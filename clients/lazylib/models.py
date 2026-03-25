from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
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
    OTHER = "other"

class UserBase(BaseModel):
    """Базовый класс с общими полями пользователя."""
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
        # 5 МБ в байтах
        MAX_IMG_SIZE = 5 * 1024 * 1024
        if v and len(v) > MAX_IMG_SIZE:
            raise ValueError(f'image too large, max {MAX_IMG_SIZE // (1024*1024)}MB')
        return v

class UserPublic(UserBase):
    """Публичный профиль пользователя (с id)."""
    id: str

class UserProfileUpdate(UserBase):
    """Обновляемые поля профиля (все опциональны)."""
    pass

class ContactRequestInput(BaseModel):
    target_id: str
    type: str  # "swap", "give", "get"
    request_id: str
    data: Optional[Dict[str, Any]] = None

class ContactRequestOut(BaseModel):
    request_id: str
    type: str
    from_id: str
    data: Optional[Dict[str, Any]] = None
    timestamp: int

class UserListResponse(BaseModel):
    items: List[UserPublic]
    total: int