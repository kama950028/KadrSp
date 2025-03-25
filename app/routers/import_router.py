from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.services.import_utils import parse_docx, import_teachers_with_programs, parse_excel, import_curriculum
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
        # Парсим данные из файла
        teachers_data = parse_docx(file_path)
        
        # Импортируем преподавателей с привязкой к программам
        import_teachers_with_programs(db, teachers_data)
    except IntegrityError as e:
        db.rollback()
        print(f"Ошибка уникальности: {e}")
    except Exception as e:
        db.rollback()
        raise e
    finally:
        # Удаляем временный файл
        os.remove(file_path)

@router.post("/upload-curriculum")
async def upload_curriculum(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(400, "Invalid file format")
    
    temp_file = f"temp_{file.filename}"
    with open(temp_file, "wb") as buffer:
        buffer.write(await file.read())
    
    try:
        data = parse_excel(temp_file)
        import_curriculum(db, data)
    except Exception as e:
        raise HTTPException(500, f"Import error: {str(e)}")
    finally:
        os.remove(temp_file)
    
    return {"message": f"Successfully imported {len(data)} records"}



@router.post("/teachers/import")
def import_teachers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Импортирует преподавателей из загруженного файла.
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .docx")

    # Сохраняем временный файл
    temp_file = f"temp_{file.filename}"
    with open(temp_file, "wb") as buffer:
        buffer.write(file.file.read())

    try:
        # Парсим данные из файла
        teachers_data = parse_docx(temp_file)
        import_teachers_with_programs(db, teachers_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка импорта преподавателей: {str(e)}")
    finally:
        os.remove(temp_file)

    return {"message": "Преподаватели успешно импортированы"}