from typing import List
from sqlalchemy.orm import Session, joinedload
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.models import Teacher, Qualification, Curriculum
from app.services.import_utils import parse_excel, import_curriculum
from app.schemas import TeacherCreate, TeacherResponse
from app.database import get_db
from typing import Optional
import os


router = APIRouter(prefix="/api", tags=["teachers"])

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


@router.get("/teachers")
def get_teachers(db: Session = Depends(get_db)):
    teachers = db.query(Teacher).all()
    return [
        {
            "teacher_id": teacher.teacher_id,
            "full_name": teacher.full_name,
            "position": teacher.position,
            "total_experience": teacher.total_experience,
            "teaching_experience": teacher.teaching_experience,
            "professional_experience": teacher.professional_experience,
            "education_level": teacher.education_level,
            "academic_degree": teacher.academic_degree,
            "academic_title": teacher.academic_title,
            "disciplines_raw": ", ".join([d.discipline_name for d in teacher.disciplines]),
            "qualifications_raw": ", ".join([q.program_name for q in teacher.qualifications]),
            "programs_raw": ", ".join([p.program_name for p in teacher.programs]),
        }
        for teacher in teachers
    ]

@router.get("/teachers/{teacher_id}", response_model=TeacherResponse)
def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Преподаватель не найден")
    return teacher





@router.get("/curriculum")
def get_curriculum(curriculum_id: Optional[int] = None, db: Session = Depends(get_db)):
    if curriculum_id:
        # Если указан curriculum_id, фильтруем по нему
        return db.query(Curriculum).filter(Curriculum.curriculum_id == curriculum_id).all()
    # Если program_id не указан, возвращаем все записи
    return db.query(Curriculum).all()
