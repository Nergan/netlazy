from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.application.auth_service import InvalidPublicKeyError
from app.domain.models import UserAlreadyExistsError
from app.presentation.dependencies import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserRegisterRequest(BaseModel):
    public_key: str = Field(..., max_length=4096, description="PEM encoded RSA public key (min 2048 bits)")

class UserRegisterResponse(BaseModel):
    user_id: str
    message: str

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserRegisterResponse)
async def register(user_data: UserRegisterRequest):
    try:
        user = await auth_service.register_user(user_data.public_key)
    except InvalidPublicKeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Public key already registered")

    return UserRegisterResponse(user_id=user.user_id, message="Registration successful")