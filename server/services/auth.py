import time
from models.user import UserInDB, UserPublic, UserProtect, UserPrivate
from core.database import get_users_collection
from services.crypto import validate_public_key
from pymongo.errors import DuplicateKeyError


async def register_user(login: str, public_key: str, key_algorithm: str = "Ed25519"):
    users_collection = await get_users_collection()

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
            requests_size_bytes=0,
            created_at=current_time,
            last_online=current_time
        )
    )
    try:
        await users_collection.insert_one(new_user.model_dump(by_alias=True))
    except DuplicateKeyError:
        raise ValueError("Login already exists")
    return login


async def change_key(login: str, new_public_key: str, new_algorithm: str):
    users_collection = await get_users_collection()

    user = await users_collection.find_one({"public.id": login})
    if not user:
        raise ValueError("User not found")

    if not validate_public_key(new_public_key, new_algorithm):
        raise ValueError("Invalid public key format or algorithm mismatch")

    result = await users_collection.update_one(
        {"public.id": login},
        {"$set": {
            "private.public_key": new_public_key,
            "private.key_algorithm": new_algorithm,
            "private.last_online": int(time.time())
        }}
    )
    if result.modified_count == 0:
        raise RuntimeError("Failed to update key")