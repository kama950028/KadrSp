from fastapi import FastAPI
from app.routers import teachers, import_router, admin
from app.database import engine, Base
import asyncio
from fastapi.staticfiles import StaticFiles

# Создаем таблицы в БД (в реальном проекте используйте миграции!)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Подключение статических файлов (CSS/JS)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключение HTML-шаблонов (если нужно)
app.mount("/templates", StaticFiles(directory="app/templates"), name="templates")

app.include_router(teachers.router)


@app.get("/")
def read_root():
    return {"message": "KadrSp API"}

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create_tables())


app.include_router(import_router.router)
app.include_router(admin.router)