from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text  # Добавьте этот импорт
from app.database import get_db, Base, engine
from app.models import Qualification, Retraining, EducationProgram, Teacher, TaughtDiscipline, Curriculum
from app.services.import_utils import import_education_programs
import os



router = APIRouter(prefix="/admin", tags=["admin"])


@router.delete("/clear-db")
def clear_database(db: Session = Depends(get_db)):
    try:
        # Удаляем все записи из таблиц
        db.query(Qualification).delete()
        db.query(TaughtDiscipline).delete()
        db.query(EducationProgram).delete()
        db.query(Teacher).delete()
        db.query(Curriculum).delete()
        
        # Сбрасываем последовательность ID для таблицы teachers
        db.execute(text("ALTER SEQUENCE teachers_teacher_id_seq RESTART WITH 1"))
        db.execute(text("ALTER SEQUENCE curriculum_id_seq RESTART WITH 1"))
        
        
        db.commit()
        return {"message": "Все данные удалены, ID сброшены"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/upload-programs")
def upload_programs(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Загружает образовательные программы из загруженного CSV-файла.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Только CSV-файлы поддерживаются.")
    
    # Сохраняем временный файл
    temp_file = f"temp_{file.filename}"
    with open(temp_file, "wb") as buffer:
        buffer.write(file.file.read())
    
    try:
        # Импортируем данные в базу
        import_education_programs(temp_file, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Удаляем временный файл
        os.remove(temp_file)
    
    return {"message": "Образовательные программы успешно загружены."}