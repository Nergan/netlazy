import imghdr
import base64
import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum


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

    @field_validator('exemplary')
    @classmethod
    def validate_exemplary_length(cls, v):
        if v:
            for item in v:
                if len(item) > 64:
                    raise ValueError('each exemplary location must be at most 64 characters')
        return v


class SexEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"


class UserPublic(BaseModel):
    id: str
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
        if not (3 <= len(v) <= 32):
            raise ValueError('id must be between 3 and 32 characters')
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', v):
            raise ValueError('id must contain only lowercase letters, digits, and hyphens, '
                             'cannot start or end with hyphen, and cannot have consecutive hyphens')
        return v

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            if len(v) < 1 or len(v) > 64:
                raise ValueError('name must be between 1 and 64 characters')
        return v

    @field_validator('desc')
    @classmethod
    def validate_desc(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError('description must be at most 500 characters')
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if v is not None:
            if len(v) > 10:
                raise ValueError('maximum 10 tags allowed')
            for tag in v:
                if len(tag) > 32:
                    raise ValueError('each tag must be at most 32 characters')
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

        if len(img_data) > 5 * 1024 * 1024:
            raise ValueError('image too large, max 5MB')

        img_type = imghdr.what(None, h=img_data)
        if img_type not in ('jpeg', 'png'):
            raise ValueError('unsupported image format, only JPEG and PNG allowed')

        return v


class UserProtect(BaseModel):
    is_online: bool = False


class UserPrivate(BaseModel):
    public_key: str
    key_algorithm: str = "Ed25519"
    requests: List[dict] = Field(default_factory=list)
    requests_size_bytes: int = 0                     # атомарно обновляемое поле размера
    created_at: int
    last_online: int


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

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            if len(v) < 1 or len(v) > 64:
                raise ValueError('name must be between 1 and 64 characters')
        return v

    @field_validator('desc')
    @classmethod
    def validate_desc(cls, v):
        if v is not None and len(v) > 500:
            raise ValueError('description must be at most 500 characters')
        return v

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if v is not None:
            if len(v) > 10:
                raise ValueError('maximum 10 tags allowed')
            for tag in v:
                if len(tag) > 32:
                    raise ValueError('each tag must be at most 32 characters')
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

        if len(img_data) > 5 * 1024 * 1024:
            raise ValueError('image too large, max 5MB')

        img_type = imghdr.what(None, h=img_data)
        if img_type not in ('jpeg', 'png'):
            raise ValueError('unsupported image format, only JPEG and PNG allowed')

        return v