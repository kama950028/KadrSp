from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
import math
from app.routers import teachers, import_router, admin, curriculum
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

# Подключение маршрутов
app.include_router(teachers.router)
app.include_router(import_router.router)
app.include_router(admin.router)
app.include_router(curriculum.router)  # Подключаем маршрут /curriculum


@app.get("/")
def read_root():
    return {"message": "KadrSp API"}

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create_tables())


def handle_nan(obj):
    if isinstance(obj, float):
        if math.isnan(obj):
            return 0.0
        return round(obj, 2)
    return obj

app.json_encoder = jsonable_encoder({
    "default": handle_nan,
    "float": lambda x: round(x, 2) if not math.isnan(x) else 0.0
})