from pydantic import BaseModel, field_validator
from enum import Enum
from typing import Optional, Dict, Any
import json
import re


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

    @field_validator('request_id')
    @classmethod
    def validate_request_id(cls, v):
        if not v:
            raise ValueError('request_id cannot be empty')
        if len(v) > 128:
            raise ValueError('request_id too long, max 128 characters')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('request_id must contain only letters, digits, underscores, and hyphens')
        return v


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

    @field_validator('request_id')
    @classmethod
    def validate_request_id(cls, v):
        if not v:
            raise ValueError('request_id cannot be empty')
        if len(v) > 128:
            raise ValueError('request_id too long, max 128 characters')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('request_id must contain only letters, digits, underscores, and hyphens')
        return v

    @field_validator('data')
    @classmethod
    def validate_data_for_give(cls, v, info):
        req_type = info.data.get('type')
        if req_type == RequestType.GIVE and (v is None or not v):
            raise ValueError('data is required for give request')
        if v is not None:
            size = len(json.dumps(v, ensure_ascii=False).encode('utf-8'))
            if size > 5 * 1024 * 1024:
                raise ValueError('data exceeds 5 MB limit')
        return v