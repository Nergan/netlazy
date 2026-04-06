import time
import json
from typing import List
from models.request import ContactRequest, ContactRequestOut, RequestType
from core.database import get_users_collection
from core.config import get_settings

MAX_PENDING_REQUESTS_SIZE_MB = get_settings().max_pending_requests_size_mb
MAX_PENDING_REQUESTS_SIZE = MAX_PENDING_REQUESTS_SIZE_MB * 1024 * 1024


async def get_pending_requests(login: str) -> List[ContactRequestOut]:
    users_collection = await get_users_collection()
    user = await users_collection.find_one(
        {"public.id": login},
        {"private.requests": 1, "_id": 0}
    )
    if not user:
        raise ValueError("User not found")
    requests_data = user.get("private", {}).get("requests", [])
    requests_data.sort(key=lambda r: r.get("timestamp", 0))
    return [ContactRequestOut(**req) for req in requests_data]


async def delete_request(login: str, request_id: str) -> bool:
    import json
    users_collection = await get_users_collection()
    # Получаем весь документ, чтобы найти удаляемый элемент
    user = await users_collection.find_one(
        {"public.id": login},
        {"private.requests": 1}
    )
    if not user:
        return False
    removed = None
    requests = user.get("private", {}).get("requests", [])
    for req in requests:
        if req.get("request_id") == request_id:
            removed = req
            break
    if not removed:
        return False
    removed_size = len(json.dumps(removed, ensure_ascii=False).encode('utf-8'))
    # Атомарно удаляем элемент
    result = await users_collection.update_one(
        {"public.id": login},
        {"$pull": {"private.requests": {"request_id": request_id}}}
    )
    if result.modified_count == 0:
        return False
    # Уменьшаем счётчик размера
    await users_collection.update_one(
        {"public.id": login},
        {"$inc": {"private.requests_size_bytes": -removed_size}}
    )
    return True


async def send_request(from_login: str, target_login: str, req_type: RequestType, request_id: str, data: dict = None):
    users_collection = await get_users_collection()

    # Проверка существования отправителя (на случай удаления после аутентификации)
    sender = await users_collection.find_one({"public.id": from_login}, {"_id": 1})
    if not sender:
        raise ValueError("Sender not found")

    if from_login == target_login:
        raise ValueError("Cannot send request to yourself")

    request_obj = ContactRequest(
        request_id=request_id,
        type=req_type,
        from_id=from_login,
        data=data,
        timestamp=int(time.time())
    ).model_dump()

    new_item_json = json.dumps(request_obj, ensure_ascii=False)
    new_item_size = len(new_item_json.encode('utf-8'))

    filter_condition = {
        "public.id": target_login,
        "private.requests.request_id": {"$ne": request_id},
        "private.requests_size_bytes": {"$lt": MAX_PENDING_REQUESTS_SIZE - new_item_size}
    }

    if req_type in (RequestType.SWAP, RequestType.GET):
        filter_condition["private.requests"] = {
            "$not": {"$elemMatch": {"from_id": from_login, "type": req_type.value}}
        }

    result = await users_collection.update_one(
        filter_condition,
        {
            "$push": {"private.requests": request_obj},
            "$inc": {"private.requests_size_bytes": new_item_size}
        }
    )

    if result.matched_count == 0:
        # Определяем причину отказа
        target_exists = await users_collection.find_one({"public.id": target_login})
        if not target_exists:
            raise ValueError("Target user not found")

        duplicate = await users_collection.find_one({
            "public.id": target_login,
            "private.requests.request_id": request_id
        })
        if duplicate:
            raise ValueError("Request with this ID already exists")

        if req_type in (RequestType.SWAP, RequestType.GET):
            existing = await users_collection.find_one({
                "public.id": target_login,
                "private.requests": {"$elemMatch": {"from_id": from_login, "type": req_type.value}}
            })
            if existing:
                raise ValueError(f"Request of type '{req_type.value}' from this user already exists")

        # Проверяем размер
        user = await users_collection.find_one(
            {"public.id": target_login},
            {"private.requests_size_bytes": 1}
        )
        if user:
            current_size = user.get("private", {}).get("requests_size_bytes", 0)
            if current_size + new_item_size > MAX_PENDING_REQUESTS_SIZE:
                raise RuntimeError(f"Target user's request queue exceeds {MAX_PENDING_REQUESTS_SIZE_MB} MB")

        raise RuntimeError("Failed to add request")