from pydantic import BaseModel
from enum import Enum
from typing import Optional, Dict, Any

class RequestType(str, Enum):
    SWAP = "swap"
    GIVE = "give"
    GET = "get"

class ContactRequest(BaseModel):
    type: RequestType
    from_id: str  # изменено
    data: Optional[Dict[str, Any]] = None
    timestamp: int

class ContactRequestOut(BaseModel):
    type: RequestType
    from_id: str  # изменено
    data: Optional[Dict[str, Any]] = None
    timestamp: int

class ContactRequestInput(BaseModel):
    target_id: str  # изменено с target_uuid
    type: RequestType
    data: Optional[Dict[str, Any]] = None