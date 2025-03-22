from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.services.import_utils import parse_docx, import_teachers
import os
import uuid

router = APIRouter(prefix="/import", tags=["import"])

@router.post("/teachers")
async def import_teachers_from_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".docx"):
        raise HTTPException(400, "Только .docx файлы поддерживаются")

    # Сохраняем файл временно
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = f"{temp_dir}/{uuid.uuid4()}.docx"
    
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())

    # Парсинг и импорт в фоне
    background_tasks.add_task(process_import, temp_path, db)
    
    return JSONResponse(
        content={"message": "Файл принят в обработку"},
        status_code=202
    )

def process_import(file_path: str, db: Session):
    try:
        teachers_data = parse_docx(file_path)
        import_teachers(db, teachers_data)
    except IntegrityError as e:
        db.rollback()
        print(f"Ошибка уникальности: {e}")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        os.remove(file_path)