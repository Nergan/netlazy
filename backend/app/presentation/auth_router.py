from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from app.application.auth_service import InvalidPublicKeyError
from app.domain.models import UserAlreadyExistsError
from app.domain.models import User
from app.presentation.dependencies import (
    auth_service, 
    profile_service, 
    inbox_service, 
    verify_pow, 
    verify_request_signature,
    profile_repo,
    handshake_repo
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserRegisterRequest(BaseModel):
    public_key: str = Field(..., max_length=4096, description="PEM encoded RSA public key (min 2048 bits)")

class UserRegisterResponse(BaseModel):
    user_id: str
    message: str

class UserRotateRequest(BaseModel):
    new_public_key: str = Field(..., max_length=4096, description="PEM encoded RSA public key (min 2048 bits)")

class UserRotateResponse(BaseModel):
    new_user_id: str
    message: str

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserRegisterResponse, dependencies=[Depends(verify_pow)])
async def register(user_data: UserRegisterRequest):
    try:
        user = await auth_service.register_user(user_data.public_key)
    except InvalidPublicKeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Public key already registered")

    return UserRegisterResponse(user_id=user.user_id, message="Registration successful")

@router.post("/rotate", response_model=UserRotateResponse)
async def rotate_key_endpoint(body: UserRotateRequest, user: User = Depends(verify_request_signature)):
    try:
        new_user_id = await auth_service.rotate_key(
            old_user_id=user.user_id,
            new_public_key_pem=body.new_public_key,
            profile_repo=profile_repo,
            handshake_repo=handshake_repo
        )
    except InvalidPublicKeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Public key already registered")

    return UserRotateResponse(new_user_id=new_user_id, message="Rotation successful")

@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(user: User = Depends(verify_request_signature)):
    await profile_service.delete_profile(user.user_id)
    await auth_service.delete_user(user.user_id)
    await inbox_service.delete_user_handshakes(user.user_id)