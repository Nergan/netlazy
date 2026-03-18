from pydantic import BaseModel
from enum import Enum
from typing import Optional, Dict, Any

class RequestType(str, Enum):
    SWAP = "swap"
    GIVE = "give"
    GET = "get"

class ContactRequest(BaseModel):
    request_id: str  # уникальный идентификатор, генерируется клиентом
    type: RequestType
    from_id: str
    data: Optional[Dict[str, Any]] = None
    timestamp: int

class ContactRequestOut(BaseModel):
    request_id: str
    type: RequestType
    from_id: str
    data: Optional[Dict[str, Any]] = None
    timestamp: int

class ContactRequestInput(BaseModel):
    target_id: str
    type: RequestType
    request_id: str  # клиент генерирует уникальный ID
    data: Optional[Dict[str, Any]] = None