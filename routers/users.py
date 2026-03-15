from typing import Optional, List
import hashlib
from fastapi import APIRouter, HTTPException, Header, Query
from models.user import UserPublic, UserPublicListResponse, UserProfileUpdate
from core.database import get_users_collection

router = APIRouter()

@router.get("/list", response_model=UserPublicListResponse)
async def list_users(
    tags: Optional[List[str]] = Query(None, description="List of tags to filter by"),
    match_all: bool = Query(True, description="If true, match all tags; if false, match any"),
    sort_by: Optional[str] = Query(None, description="Sort field: created_at, last_online, tags_match"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_password: Optional[str] = Header(None, alias="X-Password")  # для исключения себя
):
    users_collection = await get_users_collection()
    
    # Определяем текущего пользователя, если пароль передан
    current_id = None
    if x_password:
        current_id = hashlib.sha256(x_password.encode()).hexdigest()
    
    # Базовый фильтр
    match_stage = {}
    
    # Фильтр по тегам
    if tags:
        tag_list = [tag.strip() for tag in tags if tag.strip()]
        if tag_list:
            if match_all:
                match_stage["public.tags"] = {"$all": tag_list}
            else:
                match_stage["public.tags"] = {"$in": tag_list}
    
    # Исключаем текущего пользователя
    if current_id:
        match_stage["public.id"] = {"$ne": current_id}
    
    # Определяем сортировку
    effective_sort_by = sort_by
    if effective_sort_by is None:
        if tags:
            effective_sort_by = "tags_match"
        else:
            effective_sort_by = "created_at"
    
    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})
    
    # Подсчёт совпадений тегов
    if effective_sort_by == "tags_match" and tags:
        tag_list = [tag.strip() for tag in tags if tag.strip()]
        pipeline.append({
            "$addFields": {
                "matched_tags_count": {
                    "$size": {
                        "$setIntersection": [tag_list, {"$ifNull": ["$public.tags", []]}]
                    }
                }
            }
        })
        sort_field = "matched_tags_count"
        sort_direction = -1
    else:
        sort_field_map = {
            "created_at": "private.created_at",
            "last_online": "private.last_online"
        }
        sort_field = sort_field_map.get(effective_sort_by, "private.created_at")
        sort_direction = 1 if sort_order == "asc" else -1
    
    pipeline.append({"$sort": {sort_field: sort_direction}})
    pipeline.append({"$skip": offset})
    pipeline.append({"$limit": limit})
    pipeline.append({"$project": {"public": 1, "_id": 0}})
    
    cursor = users_collection.aggregate(pipeline)
    items = await cursor.to_list(length=limit)
    
    total = await users_collection.count_documents(match_stage)
    
    public_items = [UserPublic(**item["public"]) for item in items]
    return UserPublicListResponse(items=public_items, total=total)

@router.get("/{user_id}", response_model=UserPublic)
async def get_user(user_id: str):
    users_collection = await get_users_collection()
    user = await users_collection.find_one({"public.id": user_id}, {"public": 1, "_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserPublic(**user["public"])

@router.patch("/me", response_model=UserPublic)
async def update_my_profile(
    profile: UserProfileUpdate,  # используем новую модель
    x_password: str = Header(..., alias="X-Password")
):
    password_hash = hashlib.sha256(x_password.encode()).hexdigest()
    users_collection = await get_users_collection()
    
    user = await users_collection.find_one({"public.id": password_hash})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {k: v for k, v in profile.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    
    # id не может быть изменён, поэтому просто обновляем поля
    await users_collection.update_one(
        {"public.id": password_hash},
        {"$set": {f"public.{k}": v for k, v in update_data.items()}}
    )
    
    updated = await users_collection.find_one({"public.id": password_hash}, {"public": 1, "_id": 0})
    return UserPublic(**updated["public"])