from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routers import teachers, import_router, admin, curriculum
from app.database import engine, Base
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path

 

# Создаем таблицы в БД (в реальном проекте используйте миграции!)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Подключение статических файлов (CSS/JS)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключение HTML-шаблонов
templates = Jinja2Templates(directory="app/templates")

# Подключение маршрутов
app.include_router(teachers.router)
app.include_router(import_router.router)
app.include_router(admin.router)
app.include_router(curriculum.router)

@app.get("/", response_class=HTMLResponse)
def read_home(request: Request):
    """
    Главная страница с кнопками для навигации.
    """
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/teachers", response_class=HTMLResponse)
def teachers_page(request: Request):
    """
    Страница преподавателей.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/curriculum/upload", response_class=HTMLResponse)
def curriculum_upload_page(request: Request):
    """
    Страница загрузки учебных планов.
    """
    return templates.TemplateResponse("curriculum_upload.html", {"request": request})

@app.get("/curriculum/view", response_class=HTMLResponse)
def curriculum_view_page(request: Request):
    """
    Страница образовательных программ.
    """
    return templates.TemplateResponse("curriculum_view.html", {"request": request})

@app.get("/curriculum/up", response_class=HTMLResponse)
def curriculum_up_page(request: Request):
    """
    Страница образовательных программ.
    """
    return templates.TemplateResponse("curriculum_up.html", {"request": request})
