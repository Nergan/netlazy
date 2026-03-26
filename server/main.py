from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.database import connect_to_mongo, close_mongo_connection, create_indexes
from routers import auth, users, contacts

app = FastAPI(title="NetLazy API")


class CacheBodyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Сохраняем тело запроса в request.state.body
        body = await request.body()
        request.state.body = body

        # Подменяем метод receive, чтобы роутеры могли прочитать тело повторно
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}
        request._receive = receive

        response = await call_next(request)
        return response


app.add_middleware(CacheBodyMiddleware)


@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    await create_indexes()


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()


@app.get("/")
async def root():
    return {"message": "NetLazy API is running"}


# Подключаем роутеры
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(contacts.router, prefix="/contacts", tags=["contacts"])