import time
from typing import List
from models.request import ContactRequest, ContactRequestOut, RequestType
from core.database import get_users_collection

async def send_request(from_login: str, target_login: str, req_type: RequestType, request_id: str, data: dict = None):
    users_collection = await get_users_collection()
    sender = await users_collection.find_one({"public.id": from_login})
    if not sender:
        raise ValueError("Sender not found")
    target = await users_collection.find_one({"public.id": target_login})
    if not target:
        raise ValueError("Target user not found")
    if from_login == target_login:
        raise ValueError("Cannot send request to yourself")
    existing = await users_collection.find_one({
        "public.id": target_login,
        "private.requests.request_id": request_id
    })
    if existing:
        raise ValueError("Request with this ID already exists")
    request_obj = ContactRequest(
        request_id=request_id,
        type=req_type,
        from_id=from_login,
        data=data,
        timestamp=int(time.time())
    ).model_dump()
    result = await users_collection.update_one(
        {"public.id": target_login},
        {"$push": {"private.requests": request_obj}}
    )
    if result.modified_count == 0:
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