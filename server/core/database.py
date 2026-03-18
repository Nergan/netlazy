from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from logging import getLogger

from .config import settings


logger = getLogger(__name__)


class MongoDB:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


async def connect_to_mongo():
    """Установка соединения с MongoDB."""
    logger.info("Connecting to MongoDB...")
    MongoDB.client = AsyncIOMotorClient(
        settings.mongodb_uri,
        tls=True,
        tlsAllowInvalidCertificates=True  # для тестового кластера, в production лучше убрать
    )
    MongoDB.db = MongoDB.client[settings.database_name]
    logger.info("Connected to MongoDB.")

async def close_mongo_connection():
    """Закрытие соединения."""
    if MongoDB.client:
        MongoDB.client.close()
        logger.info("Closed MongoDB connection.")

async def get_users_collection():
    """Возвращает коллекцию users."""
    return MongoDB.db["users"]


async def create_indexes():
    """Создание индексов для коллекции users."""
    users = await get_users_collection()

    await users.create_index("public.id", unique=True)
    logger.debug("Index on public.id created/verified.")

    # Мультиключевой индекс по тегам
    await users.create_index("public.tags")
    logger.debug("Index on public.tags created/verified.")

    # Геоиндекс 2dsphere для точного местоположения
    await users.create_index([("public.location.precise", "2dsphere")])
    logger.debug("Geospatial index on public.location.precise created/verified.")

    # Индекс по дате создания для сортировки
    await users.create_index("private.created_at")
    logger.debug("Index on private.created_at created/verified.")

    # Составной индекс для частых фильтров (теги + дата)
    await users.create_index([("public.tags", 1), ("private.created_at", -1)])
    logger.debug("Compound index on (public.tags, private.created_at) created/verified.")

    logger.info("All indexes are set up.")