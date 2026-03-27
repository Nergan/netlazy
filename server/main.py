from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from core.database import connect_to_mongo, close_mongo_connection, create_indexes
from core.rate_limit import RateLimitMiddleware
from routers import auth, users, contacts


class CacheBodyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        body = await request.body()
        request.state.body = body
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}
        request._receive = receive
        response = await call_next(request)
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    await create_indexes()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(title="NetLazy API", lifespan=lifespan)

app.add_middleware(CacheBodyMiddleware)
app.add_middleware(RateLimitMiddleware)


@app.get("/")
async def root():
    return {"message": "NetLazy API is running"}


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(contacts.router, prefix="/contacts", tags=["contacts"])