from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from models.user import UserPublic, UserPublicListResponse, UserProfileUpdate
from services import users as users_service
from core.deps import current_user_required, current_user_optional

router = APIRouter()

@router.get("/list", response_model=UserPublicListResponse)
async def list_users(
    tags: Optional[List[str]] = Query(None),
    match_all: bool = Query(True),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_login: Optional[str] = Depends(current_user_optional)
):
    try:
        items, total = await users_service.list_users(
            current_login=current_login,
            tags=tags,
            match_all=match_all,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset
        )
        return UserPublicListResponse(items=items, total=total)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/me", response_model=UserPublic)
async def get_my_profile(login: str = Depends(current_user_required)):
    user = await users_service.get_user_by_id(login)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/{login}", response_model=UserPublic)
async def get_user(login: str):
    user = await users_service.get_user_by_id(login)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/me", response_model=UserPublic)
async def update_my_profile(
    profile: UserProfileUpdate,
    login: str = Depends(current_user_required)
):
    update_data = profile.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    try:
        updated = await users_service.update_user_profile(login, update_data)
        if not updated:
            raise HTTPException(status_code=404, detail="User not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))