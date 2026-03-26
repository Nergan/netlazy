from pydantic import BaseModel, field_validator
from enum import Enum
from typing import Optional, Dict, Any


class RequestType(str, Enum):
    SWAP = "swap"
    GIVE = "give"
    GET = "get"


class ContactRequest(BaseModel):
    request_id: str
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
    request_id: str
    data: Optional[Dict[str, Any]] = None

    @field_validator('data')
    @classmethod
    def validate_data_for_give(cls, v, info):
        # info.data содержит значения полей после парсинга
        # Проверяем, что если тип GIVE, то data не None и не пусто
        req_type = info.data.get('type')
        if req_type == RequestType.GIVE and (v is None or not v):
            raise ValueError('data is required for give request')
        return v