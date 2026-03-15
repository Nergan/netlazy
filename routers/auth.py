from fastapi import APIRouter, HTTPException, Body, Header
import hashlib
import time
from models.user import UserInDB, UserPublic, UserProtect, UserPrivate
from core.database import get_users_collection

router = APIRouter()

@router.post("/identify")
async def identify(password: str = Body(..., embed=True)):
    """
    Идентификация по паролю.
    - Если пользователь с таким хэшем существует → авторизация.
    - Иначе создаётся новый пользователь с этим хэшем в качестве public.id.
    """
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    users_collection = await get_users_collection()
    
    user = await users_collection.find_one({"public.id": password_hash})
    if user:
        # Обновляем время последнего онлайна
        await users_collection.update_one(
            {"public.id": password_hash},
            {"$set": {"private.last_online": int(time.time())}}
        )
        return {"status": "authenticated", "id": password_hash}
    else:
        # Создаём нового пользователя
        current_time = int(time.time())
        new_user = UserInDB(
            public=UserPublic(id=password_hash),
            protect=UserProtect(),
            private=UserPrivate(
                requests=[],
                created_at=current_time,
                last_online=current_time
            )
        )
        await users_collection.insert_one(new_user.model_dump(by_alias=True))
        return {"status": "created", "id": password_hash}

@router.post("/change-password")
async def change_password(
    old_password: str = Body(...),
    new_password: str = Body(...),
    x_password: str = Header(..., alias="X-Password")  # текущий пароль для подтверждения
):
    # Проверяем, что старый пароль совпадает с текущим
    old_hash = hashlib.sha256(old_password.encode()).hexdigest()
    if old_hash != hashlib.sha256(x_password.encode()).hexdigest():
        raise HTTPException(status_code=401, detail="Old password mismatch")
    
    new_hash = hashlib.sha256(new_password.encode()).hexdigest()
    users_collection = await get_users_collection()
    
    # Проверяем уникальность нового хэша
    existing = await users_collection.find_one({"public.id": new_hash})
    if existing:
        raise HTTPException(status_code=400, detail="New password already in use")
    
    # Обновляем public.id
    result = await users_collection.update_one(
        {"public.id": old_hash},
        {"$set": {"public.id": new_hash}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"status": "password changed", "new_id": new_hash}