import logging
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING
from app.config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None
    users_collection = None
    used_nonces_collection = None
    tags_collection = None
    profiles_collection = None
    handshakes_collection = None

db_instance = Database()

async def connect_to_mongo():
    logging.info("Connecting to MongoDB...")

    kwargs = {}
    if settings.mongo_tls:
        kwargs["tls"] = True
    if settings.mongo_tls_allow_invalid_certificates:
        kwargs["tlsAllowInvalidCertificates"] = True

    db_instance.client = AsyncIOMotorClient(settings.mongodb_uri, **kwargs)
    db_instance.db = db_instance.client.netlazy_db

    db_instance.users_collection = db_instance.db.users
    db_instance.used_nonces_collection = db_instance.db.used_nonces
    db_instance.tags_collection = db_instance.db.tags
    db_instance.profiles_collection = db_instance.db.profiles
    db_instance.handshakes_collection = db_instance.db.handshakes

    await db_instance.users_collection.create_index("user_id", unique=True)

    await db_instance.used_nonces_collection.create_index(
        [("user_id", ASCENDING), ("nonce", ASCENDING)],
        unique=True
    )
    await db_instance.used_nonces_collection.create_index("created_at", expireAfterSeconds=300)

    await db_instance.tags_collection.create_index("name", unique=True)
    await db_instance.profiles_collection.create_index("user_id", unique=True)
    await db_instance.profiles_collection.create_index("created_at")

    await db_instance.handshakes_collection.create_index("sender_id")
    await db_instance.handshakes_collection.create_index("receiver_id")

    logging.info("Connected to MongoDB successfully.")

async def close_mongo_connection():
    if db_instance.client:
        db_instance.client.close()
        logging.info("Closed MongoDB connection.")