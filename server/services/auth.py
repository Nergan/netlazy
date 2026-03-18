import time
from models.user import UserInDB, UserPublic, UserProtect, UserPrivate
from core.database import get_users_collection
from services.crypto import validate_public_key

async def register_user(login: str, public_key: str, key_algorithm: str = "Ed25519"):
    """
    Регистрирует нового пользователя.
    Проверяет уникальность логина и корректность публичного ключа.
    """
    users_collection = await get_users_collection()
    
    # Проверка уникальности логина
    existing = await users_collection.find_one({"public.id": login})
    if existing:
        raise ValueError("Login already exists")
    
    # Проверка формата ключа
    if not validate_public_key(public_key, key_algorithm):
        raise ValueError("Invalid public key format or algorithm mismatch")
    
    current_time = int(time.time())
    new_user = UserInDB(
        public=UserPublic(id=login),
        protect=UserProtect(),
        private=UserPrivate(
            public_key=public_key,
            key_algorithm=key_algorithm,
            requests=[],
            created_at=current_time,
            last_online=current_time
        )
    )
    await users_collection.insert_one(new_user.model_dump(by_alias=True))
    return login

async def change_key(login: str, new_public_key: str, new_algorithm: str):
    """
    Меняет публичный ключ пользователя.
    Требуется предварительная аутентификация (вызывается только для current_user).
    """
    users_collection = await get_users_collection()
    
    # Проверка существования пользователя
    user = await users_collection.find_one({"public.id": login})
    if not user:
        raise ValueError("User not found")
    
    # Проверка нового ключа
    if not validate_public_key(new_public_key, new_algorithm):
        raise ValueError("Invalid public key format or algorithm mismatch")
    
    # Обновление
    result = await users_collection.update_one(
        {"public.id": login},
        {"$set": {
            "private.public_key": new_public_key,
            "private.key_algorithm": new_algorithm
        }}
    )
    if result.modified_count == 0:
        raise RuntimeError("Failed to update key")