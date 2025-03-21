from fastapi import FastAPI
from app.routers import teachers
from app.database import engine, Base
import asyncio


# Создаем таблицы в БД (в реальном проекте используйте миграции!)
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(teachers.router)

@app.get("/")
def read_root():
    return {"message": "KadrSp API"}

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create_tables())