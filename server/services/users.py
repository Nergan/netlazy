import base64
from typing import Optional, List
from models.user import UserPublic, UserProfileUpdate
from core.database import get_users_collection

async def get_user_by_id(login: str) -> Optional[UserPublic]:
    users_collection = await get_users_collection()
    user = await users_collection.find_one({"public.id": login}, {"public": 1, "_id": 0})
    if not user:
        return None
    public_data = user["public"]
    if public_data.get("img") and isinstance(public_data["img"], bytes):
        public_data["img"] = base64.b64encode(public_data["img"]).decode('ascii')
    return UserPublic(**public_data)

async def update_user_profile(login: str, update_data: dict) -> Optional[UserPublic]:
    users_collection = await get_users_collection()
    if "img" in update_data and update_data["img"] is not None:
        try:
            update_data["img"] = base64.b64decode(update_data["img"])
        except Exception:
            raise ValueError("Invalid base64 image")
    update_dict = {f"public.{k}": v for k, v in update_data.items()}
    result = await users_collection.update_one(
        {"public.id": login},
        {"$set": update_dict}
    )
    if result.matched_count == 0:
        return None
    updated = await users_collection.find_one({"public.id": login}, {"public": 1, "_id": 0})
    public_data = updated["public"]
    if public_data.get("img") and isinstance(public_data["img"], bytes):
        public_data["img"] = base64.b64encode(public_data["img"]).decode('ascii')
    return UserPublic(**public_data)

async def list_users(
    current_login: Optional[str],
    tags: Optional[List[str]],
    match_all: bool,
    sort_by: Optional[str],
    sort_order: str,
    limit: int,
    offset: int
) -> tuple[List[UserPublic], int]:
    users_collection = await get_users_collection()
    match_stage = {}
    effective_tags = None
    if tags:
        tag_list = [t.strip() for t in tags if t.strip()]
        if tag_list:
            effective_tags = tag_list
            if match_all:
                match_stage["public.tags"] = {"$all": tag_list}
            else:
                match_stage["public.tags"] = {"$in": tag_list}

    if current_login:
        match_stage["public.id"] = {"$ne": current_login}

    effective_sort_by = sort_by
    if effective_sort_by is None:
        if effective_tags:
            effective_sort_by = "tags_match"
        else:
            effective_sort_by = "created_at"

    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    if effective_sort_by == "tags_match" and effective_tags:
        pipeline.append({
            "$addFields": {
                "matched_tags_count": {
                    "$size": {
                        "$setIntersection": [effective_tags, {"$ifNull": ["$public.tags", []]}]
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

    public_items = []
    for item in items:
        pub = item["public"]
        if pub.get("img") and isinstance(pub["img"], bytes):
            pub["img"] = base64.b64encode(pub["img"]).decode('ascii')
        public_items.append(UserPublic(**pub))
    return public_items, total