from pydantic import BaseModel, Field
from typing import Optional, List

class LocationPrecise(BaseModel):
    type: str = "Point"
    coordinates: List[float]

class Location(BaseModel):
    precise: Optional[LocationPrecise] = None
    exemplary: Optional[List[str]] = None

class UserPublic(BaseModel):
    id: str
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    desc: Optional[str] = None
    img: Optional[bytes] = None
    location: Optional[Location] = None
    tags: Optional[List[str]] = None

class ContactItem(BaseModel):
    is_public: bool
    contact: str

class UserProtect(BaseModel):
    contacts: Optional[List[ContactItem]] = Field(default_factory=list)
    is_online: bool = False

class UserPrivate(BaseModel):
    requests: List[str] = Field(default_factory=list)
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
    sex: Optional[str] = None
    desc: Optional[str] = None
    img: Optional[bytes] = None
    location: Optional[Location] = None
    tags: Optional[List[str]] = None