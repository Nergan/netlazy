from fastapi import FastAPI

from core.database import connect_to_mongo, close_mongo_connection, create_indexes
from routers import auth, users, contacts


app = FastAPI(title="NetLazy API")


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