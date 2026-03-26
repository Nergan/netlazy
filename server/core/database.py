from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from logging import getLogger

from .config import settings

logger = getLogger(__name__)


class MongoDB:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    MongoDB.client = AsyncIOMotorClient(
        settings.mongodb_uri,
        tls=True,
        tlsAllowInvalidCertificates=settings.mongodb_tls_allow_invalid
    )
    MongoDB.db = MongoDB.client[settings.database_name]
    logger.info("Connected to MongoDB.")


async def close_mongo_connection():
    if MongoDB.client:
        MongoDB.client.close()
        logger.info("Closed MongoDB connection.")


async def get_users_collection():
    return MongoDB.db["users"]


async def create_indexes():
    users = await get_users_collection()

    await users.create_index("public.id", unique=True)
    logger.debug("Index on public.id created/verified.")

    await users.create_index("public.tags")
    logger.debug("Index on public.tags created/verified.")

    await users.create_index([("public.location.precise", "2dsphere")])
    logger.debug("Geospatial index on public.location.precise created/verified.")

    await users.create_index("private.created_at")
    logger.debug("Index on private.created_at created/verified.")

    await users.create_index([("public.tags", 1), ("private.created_at", -1)])
    logger.debug("Compound index on (public.tags, private.created_at) created/verified.")

    await users.create_index("private.requests.request_id")
    logger.debug("Index on private.requests.request_id created/verified.")

    await users.create_index([("private.requests.from_id", 1), ("private.requests.type", 1)])
    logger.debug("Compound index on (private.requests.from_id, private.requests.type) created/verified.")

    # Индекс для поля размера очереди (для оптимизации, не критично)
    await users.create_index("private.requests_size_bytes")
    logger.debug("Index on private.requests_size_bytes created/verified.")

    logger.info("All indexes are set up.")