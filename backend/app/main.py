import logging
import mimetypes
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.presentation import auth_router, profile_router, tag_router, feed_router, inbox_router, security_router
from app.presentation.dependencies import tag_service

# Windows registry fix: explicitly map module files to correct types
# overriding misconfigured system register environments
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

# Privacy and Security Filter: Suppress logging of sensitive routes
class SensitiveRouteFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.args and len(record.args) >= 3:
            path = record.args[2]
            if isinstance(path, str) and ("/resolve" in path or "/handshakes" in path or "/me" in path):
                return False
        message = record.getMessage()
        if "/resolve" in message or "/handshakes" in message or "/me" in message:
            return False
        return True

logging.getLogger("uvicorn.access").addFilter(SensitiveRouteFilter())

class MongoLogHandler(logging.Handler):
    def emit(self, record):
        from app.database import db_instance
        if db_instance.logs_collection is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
            
        log_doc = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc),
            "level": record.levelname,
            "name": record.name,
            "message": self.format(record)
        }
        loop.create_task(db_instance.logs_collection.insert_one(log_doc))

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    
    mongo_handler = MongoLogHandler()
    mongo_handler.setLevel(logging.INFO)
    mongo_handler.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(mongo_handler)

    synced_count = await tag_service.sync_from_yaml(settings.tags_yaml_path)
    logging.info(f"Tag registry synced: {synced_count} tags loaded from {settings.tags_yaml_path}")

    yield
    logging.getLogger().removeHandler(mongo_handler)
    await close_mongo_connection()

app = FastAPI(title="netlazy API", lifespan=lifespan)

# Mount API Routers
app.include_router(auth_router.router, prefix="/api")
app.include_router(tag_router.router, prefix="/api")
app.include_router(profile_router.router, prefix="/api")
app.include_router(feed_router.router, prefix="/api")
app.include_router(inbox_router.router, prefix="/api")
app.include_router(security_router.router, prefix="/api")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "auth_type": "per-request-signature"}

# Mount Static Files for Vue SPA
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    # Catch-all to serve index.html for Vue's SPA history mode
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "Frontend build not found. Run Vite build first."}
else:
    logging.warning("Static directory not found. Frontend will not be served.")