from fastapi import APIRouter, UploadFile, File, Depends, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.services.import_utils import parse_docx, import_teachers_with_programs, parse_excel, import_curriculum
import os
import uuid
import zipfile
from io import BytesIO 
import time
import tempfile

router = APIRouter(prefix="/import", tags=["import"])


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

# def safe_remove(file_path):
#     try:
#         if os.path.exists(file_path):
#             os.remove(file_path)
#             print(f"Файл {file_path} успешно удалён.")
#     except PermissionError as e:
#         print(f"Не удалось удалить файл {file_path}: {e}")
#     except Exception as e:
#         print(f"Ошибка при удалении файла {file_path}: {e}")

def safe_remove_with_retry(file_path, max_retries=5, delay=1):
    for attempt in range(max_retries):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Файл {file_path} успешно удалён на попытке {attempt + 1}.")
            return
        except PermissionError as e:
            print(f"Попытка {attempt + 1}: Не удалось удалить файл {file_path}: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
        except Exception as e:
            print(f"Ошибка при удалении файла {file_path}: {e}")
            break
    print(f"Не удалось удалить файл {file_path} после {max_retries} попыток.")

@router.post("/upload-curriculum")
async def upload_curriculum_endpoint(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name  # Получаем путь к временному файлу

        # Обрабатываем файл
        result = import_curriculum(
            file_path=temp_path,
            filename=file.filename,
            db=db,
            background_tasks=background_tasks
        )

        # Добавляем задачу удаления файла в фоновые задачи
        # background_tasks.add_task(safe_remove, temp_path)
        background_tasks.add_task(safe_remove_with_retry, temp_path)

        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        raise HTTPException(500, detail=str(e))

@router.post("/teachers/import")
def import_teachers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Импортирует преподавателей из загруженного файла.
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .docx")

    try:
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            temp_file.write(file.file.read())
            temp_path = temp_file.name  # Получаем путь к временному файлу

        # Парсим данные из файла
        teachers_data = parse_docx(temp_path)
        import_teachers_with_programs(db, teachers_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка импорта преподавателей: {str(e)}")
    finally:
        safe_remove(temp_path)  # Удаляем временный файл

    return {"message": "Преподаватели успешно импортированы"}