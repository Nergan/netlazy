import time
from typing import List
from models.request import ContactRequest, ContactRequestOut, RequestType
from core.database import get_users_collection


async def send_request(from_login: str, target_login: str, req_type: RequestType, request_id: str, data: dict = None):
    users_collection = await get_users_collection()

    # Проверка существования отправителя и получателя
    sender = await users_collection.find_one({"public.id": from_login})
    if not sender:
        raise ValueError("Sender not found")
    target = await users_collection.find_one({"public.id": target_login})
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

    if req_type in (RequestType.SWAP, RequestType.GET):
        # Для swap и get: запрещаем второй запрос того же типа от того же отправителя
        result = await users_collection.find_one_and_update(
            {
                "public.id": target_login,
                "private.requests": {
                    "$not": {"$elemMatch": {"from_id": from_login, "type": req_type.value}}
                }
            },
            {"$push": {"private.requests": request_obj}},
            return_document=False
        )
        if result is None:
            # Проверяем, существует ли уже такой запрос
            existing = await users_collection.find_one({
                "public.id": target_login,
                "private.requests": {"$elemMatch": {"from_id": from_login, "type": req_type.value}}
            })
            if existing:
                raise ValueError(f"Request of type '{req_type.value}' from this user already exists")
            else:
                raise RuntimeError("Failed to add request")
    else:  # give
        # Для give: запрещаем только дубликат request_id
        result = await users_collection.find_one_and_update(
            {
                "public.id": target_login,
                "private.requests.request_id": {"$ne": request_id}
            },
            {"$push": {"private.requests": request_obj}},
            return_document=False
        )
        if result is None:
            duplicate = await users_collection.find_one({
                "public.id": target_login,
                "private.requests.request_id": request_id
            })
            if duplicate:
                raise ValueError("Request with this ID already exists")
            else:
                raise RuntimeError("Failed to add request")


async def check_requests(login: str) -> List[ContactRequestOut]:
    users_collection = await get_users_collection()
    user = await users_collection.find_one_and_update(
        {"public.id": login},
        {"$set": {"private.requests": []}},
        projection={"private.requests": 1, "_id": 0},
        return_document=False
    )
    if not user:
        raise ValueError("User not found")
    requests_data = user.get("private", {}).get("requests", [])
    return [ContactRequestOut(**req) for req in requests_data]