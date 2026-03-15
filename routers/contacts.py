from typing import List, Optional
import json
import time
import hashlib
from fastapi import APIRouter, HTTPException, Header, status
from models.request import ContactRequestInput, ContactRequest, ContactRequestOut
from core.database import get_users_collection

router = APIRouter()

@router.post("/request", status_code=status.HTTP_202_ACCEPTED)
async def send_contact_request(
    request_data: ContactRequestInput,
    x_password: str = Header(..., alias="X-Password")
):
    # Идентифицируем отправителя
    from_id = hashlib.sha256(x_password.encode()).hexdigest()
    users_collection = await get_users_collection()
    
    # Проверяем, что отправитель существует
    sender = await users_collection.find_one({"public.id": from_id})
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    # Проверяем, что целевой пользователь существует
    target = await users_collection.find_one({"public.id": request_data.target_id})
    if not target:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Нельзя отправить запрос самому себе
    if request_data.target_id == from_id:
        raise HTTPException(status_code=400, detail="Cannot send request to yourself")
    
    # Формируем запрос
    request_obj = ContactRequest(
        type=request_data.type,
        from_id=from_id,  # изменено с from_uuid
        data=request_data.data,
        timestamp=int(time.time())
    )
    request_json = request_obj.model_dump_json()
    
    # Добавляем в очередь цели
    result = await users_collection.update_one(
        {"public.id": request_data.target_id},
        {"$push": {"private.requests": request_json}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to add request")
    
    return {"status": "request sent"}

@router.get("/check", response_model=List[ContactRequestOut])
async def check_requests(x_password: str = Header(..., alias="X-Password")):
    user_id = hashlib.sha256(x_password.encode()).hexdigest()
    users_collection = await get_users_collection()
    
    # Атомарно получаем и очищаем очередь
    user = await users_collection.find_one_and_update(
        {"public.id": user_id},
        {"$set": {"private.requests": []}},
        projection={"private.requests": 1, "_id": 0},
        return_document=False
    )
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    requests_json = user.get("private", {}).get("requests", [])
    parsed = []
    for req_str in requests_json:
        try:
            req_data = json.loads(req_str)
            parsed.append(ContactRequestOut(**req_data))
        except Exception as e:
            print(f"Failed to parse request: {e}")
    
    return parsed