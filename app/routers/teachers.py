from typing import List
from sqlalchemy.orm import Session, joinedload
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.models import Teacher, Qualification, Curriculum
from app.services.import_utils import parse_excel, import_curriculum, assign_teacher_to_program, import_teachers_with_programs, parse_docx
from app.schemas import TeacherCreate, TeacherResponse
from app.database import get_db

from typing import Optional
import os, docx


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
    teachers = db.query(Teacher).options(joinedload(Teacher.programs)).all()
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
            "disciplines_raw": ", ".join([d.discipline for d in teacher.disciplines]),  # Исправлено
            "qualifications_raw": ", ".join([q.program_name for q in teacher.qualifications]),
            "programs": [
                {
                    "program_id": p.program_id,
                    "program_name": p.program_name
                }
                for p in teacher.programs
            ],  # Добавлено program_id
        }
        for teacher in teachers
    ]


@router.get("/teachers/{teacher_id}", response_model=TeacherResponse)
def get_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.query(Teacher).filter(Teacher.teacher_id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Преподаватель не найден")
    return teacher


@router.post("/teachers/{teacher_id}/assign-program/{program_id}")
def assign_program_to_teacher(teacher_id: int, program_id: int, db: Session = Depends(get_db)):
    """
    Привязывает преподавателя к образовательной программе.
    """
    try:
        assign_teacher_to_program(db, teacher_id, program_id)
        return {"message": f"Преподаватель с ID {teacher_id} привязан к программе с ID {program_id}"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/teachers/import")

def import_teachers(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Импортирует преподавателей из загруженного файла и привязывает их к образовательным программам.
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .docx")

    # Сохраняем временный файл
    temp_file = f"temp_{file.filename}"
    with open(temp_file, "wb") as buffer:
        buffer.write(file.file.read())

    try:
        # Парсим данные из файла
        teachers_data = parse_docx(temp_file)  # Функция для парсинга docx
        import_teachers_with_programs(db, teachers_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка импорта преподавателей: {str(e)}")
    finally:
        os.remove(temp_file)

    return {"message": "Преподаватели успешно импортированы"}





