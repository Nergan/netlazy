import time
import json
from typing import List
from models.request import ContactRequest, ContactRequestOut, RequestType
from core.database import get_users_collection
from core.config import settings

MAX_PENDING_REQUESTS_SIZE = settings.max_pending_requests_size_mb * 1024 * 1024


async def get_pending_requests(login: str) -> List[ContactRequestOut]:
    users_collection = await get_users_collection()
    user = await users_collection.find_one(
        {"public.id": login},
        {"private.requests": 1, "_id": 0}
    )
    if not user:
        raise ValueError("User not found")
    requests_data = user.get("private", {}).get("requests", [])
    # Сортируем по timestamp (по возрастанию)
    requests_data.sort(key=lambda r: r.get("timestamp", 0))
    return [ContactRequestOut(**req) for req in requests_data]


async def delete_request(login: str, request_id: str) -> bool:
    users_collection = await get_users_collection()
    # Находим документ, чтобы получить размер удаляемого запроса
    user = await users_collection.find_one(
        {"public.id": login, "private.requests.request_id": request_id},
        {"private.requests": 1}
    )
    if not user:
        return False

    # Ищем нужный запрос и его размер
    target = None
    for req in user["private"].get("requests", []):
        if req["request_id"] == request_id:
            target = req
            break
    if not target:
        return False

    # Вычисляем размер
    target_size = len(json.dumps(target, ensure_ascii=False).encode('utf-8'))

    # Атомарное удаление и уменьшение размера
    result = await users_collection.update_one(
        {"public.id": login, "private.requests.request_id": request_id},
        {
            "$pull": {"private.requests": {"request_id": request_id}},
            "$inc": {"private.requests_size_bytes": -target_size}
        }
    )
    return result.modified_count > 0


async def send_request(from_login: str, target_login: str, req_type: RequestType, request_id: str, data: dict = None):
    users_collection = await get_users_collection()

    # Проверка существования получателя и получение текущего документа
    target = await users_collection.find_one(
        {"public.id": target_login},
        {"private.requests": 1, "private.requests_size_bytes": 1}
    )
    if not target:
        raise ValueError("Target user not found")

    if from_login == target_login:
        raise ValueError("Cannot send request to yourself")

    request_obj = ContactRequest(
        request_id=request_id,
        type=req_type,
        from_id=from_login,
        data=data,
        timestamp=int(time.time())
    ).model_dump()

    # Вычисляем размер нового элемента
    new_item_json = json.dumps(request_obj, ensure_ascii=False)
    new_item_size = len(new_item_json.encode('utf-8'))

    # Проверяем, что размер очереди не превысит лимит
    current_size = target.get("private", {}).get("requests_size_bytes", 0)
    if current_size + new_item_size > MAX_PENDING_REQUESTS_SIZE:
        raise RuntimeError(f"Target user's request queue exceeds {settings.max_pending_requests_size_mb} MB")

    # Базовый фильтр: нет дубликата request_id
    filter_condition = {
        "public.id": target_login,
        "private.requests.request_id": {"$ne": request_id}
    }

    # Для swap и get: запрещаем второй запрос того же типа от того же отправителя
    if req_type in (RequestType.SWAP, RequestType.GET):
        filter_condition["private.requests"] = {
            "$not": {"$elemMatch": {"from_id": from_login, "type": req_type.value}}
        }

    # Атомарное добавление с проверкой дубликата request_id и увеличением размера
    result = await users_collection.update_one(
        filter_condition,
        {
            "$push": {"private.requests": request_obj},
            "$inc": {"private.requests_size_bytes": new_item_size}
        }
    )

    if result.matched_count == 0:
        # Определяем причину отказа
        if req_type in (RequestType.SWAP, RequestType.GET):
            existing = await users_collection.find_one({
                "public.id": target_login,
                "private.requests": {"$elemMatch": {"from_id": from_login, "type": req_type.value}}
            })
            if existing:
                raise ValueError(f"Request of type '{req_type.value}' from this user already exists")

        duplicate = await users_collection.find_one({
            "public.id": target_login,
            "private.requests.request_id": request_id
        })
        if duplicate:
            raise ValueError("Request with this ID already exists")

        raise RuntimeError("Failed to add request")