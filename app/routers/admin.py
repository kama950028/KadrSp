from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text  # Добавьте этот импорт
from app.database import get_db, Base, engine
from app.models import Qualification, Retraining, EducationProgram, Teacher, TaughtDiscipline


router = APIRouter(prefix="/admin", tags=["admin"])


@router.delete("/clear-db")
def clear_database(db: Session = Depends(get_db)):
    try:
        # Удаляем все записи из таблиц
        db.query(Qualification).delete()
        db.query(TaughtDiscipline).delete()
        db.query(EducationProgram).delete()
        db.query(Teacher).delete()
        
        # Сбрасываем последовательность ID для таблицы teachers
        db.execute(text("ALTER SEQUENCE teachers_teacher_id_seq RESTART WITH 1"))
        
        db.commit()
        return {"message": "Все данные удалены, ID сброшены"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))