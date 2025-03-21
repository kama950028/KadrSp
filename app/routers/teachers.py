from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from app.models import Teacher, Qualification
from app.schemas import TeacherCreate, TeacherResponse
from app.database import get_db

router = APIRouter(prefix="/teachers", tags=["teachers"])

@router.post("/", response_model=TeacherResponse)
def create_teacher(teacher: TeacherCreate, db: Session = Depends(get_db)):
    # Проверка на уникальность ФИО
    db_teacher = db.query(Teacher).filter(Teacher.full_name == teacher.full_name).first()
    if db_teacher:
        raise HTTPException(status_code=400, detail="Преподаватель уже существует")
    
    # Создаем преподавателя
    new_teacher = Teacher(
        full_name=teacher.full_name,
        position=teacher.position,
        education_level=teacher.education_level
    )
    
    # Добавляем квалификации
    for qual in teacher.qualifications:
        qualification = Qualification(**qual.dict())
        new_teacher.qualifications.append(qualification)
    
    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    return new_teacher

@router.get("/{teacher_id}", response_model=TeacherResponse)
def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Преподаватель не найден")
    return teacher