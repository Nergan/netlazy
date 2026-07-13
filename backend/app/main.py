import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.presentation import auth_router, profile_router, tag_router, feed_router, inbox_router
from app.presentation.dependencies import tag_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()

    synced_count = await tag_service.sync_from_yaml(settings.tags_yaml_path)
    logging.info(f"Tag registry synced: {synced_count} tags loaded from {settings.tags_yaml_path}")

    yield
    await close_mongo_connection()

app = FastAPI(title="netlazy API", lifespan=lifespan)

app.include_router(auth_router.router)
app.include_router(tag_router.router)
app.include_router(profile_router.router)
app.include_router(feed_router.router)
app.include_router(inbox_router.router)

@app.get("/")
def root():
    return {"status": "ok", "auth_type": "per-request-signature"}