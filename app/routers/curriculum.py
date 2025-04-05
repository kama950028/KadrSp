from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from app.models import Curriculum, EducationProgram, TaughtDiscipline, Teacher
from app.database import get_db
from app.schemas import CurriculumBase, EducationProgramBase
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import selectinload
from fastapi.responses import FileResponse
import logging
from pathlib import Path
import os
from sqlalchemy import func


templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


@router.get("/view", response_class=HTMLResponse)
def curriculum_view(request: Request):
    """
    Рендер страницы с выбором образовательной программы.
    """
    return templates.TemplateResponse("curriculum_view.html", {"request": request})


# @router.get("/", response_model=List[CurriculumBase])
# def get_curriculum(curriculum_id: Optional[int] = None, db: Session = Depends(get_db)):
#     """
#     Получить список дисциплин учебных планов.
#     Если указан `curriculum_id`, возвращает конкретную дисциплину учебного плана.
#     """
#     query = db.query(Curriculum).options(joinedload(Curriculum.program))

#     if curriculum_id:
#         curriculum = query.filter(Curriculum.curriculum_id == curriculum_id).first()
#         if not curriculum:
#             raise HTTPException(status_code=404, detail="Учебный план не найден")
#         return [curriculum]

#     return query.all()

# @router.get("/", response_model=List[CurriculumBase])
# def get_curriculum(curriculum_id: Optional[int] = None, db: Session = Depends(get_db)):
#     """
#     Получить список дисциплин учебных планов с привязанными преподавателями.
#     """
#     query = db.query(Curriculum).options(
#         joinedload(Curriculum.teachers)
#     )

#     if curriculum_id:
#         curriculum = query.filter(Curriculum.curriculum_id == curriculum_id).first()
#         if not curriculum:
#             raise HTTPException(status_code=404, detail="Учебный план не найден")
#         return [curriculum]

#     return query.all()


@router.get("/", response_model=List[CurriculumBase])
def get_curriculum(
    curriculum_id: Optional[int] = None,
    program_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Получить список дисциплин учебных планов с привязанными преподавателями.
    """
    # Загружаем дисциплины с привязанными преподавателями
    query = db.query(Curriculum).options(
        joinedload(Curriculum.teachers)  # Загружаем связанных преподавателей
    )

    # Фильтрация по curriculum_id
    if curriculum_id:
        curriculum = query.filter(Curriculum.curriculum_id == curriculum_id).first()
        if not curriculum:
            raise HTTPException(status_code=404, detail="Учебный план не найден")
        return [curriculum]

    # Фильтрация по program_id
    if program_id:
        query = query.filter(Curriculum.program_id == program_id)

    # Отладка: вывод данных для проверки
    results = query.all()
    print("\nDEBUG INFO:")
    for curriculum in results:
        print(f"Discipline: {curriculum.discipline}")
        if hasattr(curriculum, "teachers"):
            print(f"  Teachers count: {len(curriculum.teachers)}")
            for teacher in curriculum.teachers:
                print(f"    - {teacher.full_name}")
        else:
            print("  No teachers attribute!")

    return results


# @router.get("/EducationProgram")
# def get_education_programs(program_id: Optional[int] = None, db: Session = Depends(get_db)):
#     """
#     Получить список образовательных программ с их связанными дисциплинами и преподавателями.
#     Возвращает только те программы, у которых есть связанные дисциплины и преподаватели.
#     """
#     query = db.query(EducationProgram).options(
#         joinedload(EducationProgram.curriculum).joinedload(Curriculum.teachers)
#     )

#     if program_id:
#         program = query.filter(EducationProgram.program_id == program_id).first()
#         if not program:
#             raise HTTPException(status_code=404, detail="Образовательная программа не найдена")
#         return program

#     # Фильтруем программы, у которых есть связанные дисциплины и преподаватели
#     programs = query.all()
#     filtered_programs = [
#         program for program in programs
#         if program.curriculum and any(curriculum.teachers for curriculum in program.curriculum)
#     ]

#     return filtered_programs


@router.get("/EducationProgram", response_model=List[EducationProgramBase])
def get_education_programs(db: Session = Depends(get_db)):
    programs = (
        db.query(EducationProgram)
        .options(
            selectinload(EducationProgram.curriculum).selectinload(Curriculum.teachers)
        )
        .all()
    )

    # Отладочный вывод
    for program in programs:
        print(f"\nПрограмма: {program.program_name}")
        for curr in program.curriculum:
            print(f"  Дисциплина: {curr.discipline}")
            print(f"  Преподаватели: {[t.full_name for t in curr.teachers]}")

    return programs


@router.get("/test_teachers/{curriculum_id}")
def test_teachers(curriculum_id: int, db: Session = Depends(get_db)):
    curriculum = (
        db.query(Curriculum)
        .options(selectinload(Curriculum.teachers))
        .filter(Curriculum.curriculum_id == curriculum_id)
        .first()
    )

    if not curriculum:
        raise HTTPException(404, "Discipline not found")

    return {
        "discipline": curriculum.discipline,
        "teachers": [t.full_name for t in curriculum.teachers],
    }


@router.get("/debug_teachers")
def debug_teachers(db: Session = Depends(get_db)):
    query = (
        db.query(
            TaughtDiscipline,
            Teacher,
            Curriculum,
            EducationProgram.program_id,
        )
        .join(Teacher, TaughtDiscipline.teacher_id == Teacher.teacher_id)
        .join(Curriculum, TaughtDiscipline.curriculum_id == Curriculum.curriculum_id)
        .join(EducationProgram, Curriculum.program_id == EducationProgram.program_id)
    )
    results = query.all()
    print("Debug results:", results)  # Логирование для отладки
    return [
        {
            "program_id": program_id,
            "program_name": curriculum.program.program_name if curriculum and curriculum.program else None,
            "discipline": curriculum.discipline if curriculum else None,
            "department": curriculum.department if curriculum else None,
            "curriculum_id": link.curriculum_id if link else None,
            "teacher": {
                "teacher_id": teacher.teacher_id if teacher else None,
                "full_name": teacher.full_name if teacher else None,
                "position": teacher.position if teacher else None,
            },
        }
        for link, teacher, curriculum, program_id in results
    ]


# @router.get("/EducationProgram", response_model=List[EducationProgramBase])
# def get_education_programs(db: Session = Depends(get_db)):
#     programs = db.query(EducationProgram).options(
#         joinedload(EducationProgram.curriculum).joinedload(Curriculum.teachers)
#     ).all()

#     # Отладка
#     print("\nDEBUG INFO:")
#     for program in programs:
#         print(f"\nProgram: {program.program_name}")
#         for curr in program.curriculum:
#             print(f"  Discipline: {curr.discipline}")
#             if hasattr(curr, 'teachers'):
#                 print(f"  Teachers count: {len(curr.teachers)}")
#                 for teacher in curr.teachers:
#                     print(f"    - {teacher.full_name}")
#             else:
#                 print("  No teachers attribute!")

#     return programs

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")


@router.get("/curriculum/up")
async def get_curriculum_page():
    """Отдает HTML страницу просмотра учебного плана"""
    file_path = os.path.join(TEMPLATES_DIR, "curriculum_up.html")

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, detail=f"File not found. Searched at: {file_path}"
        )

    return FileResponse(file_path)


@router.get("/programs", response_model=List[EducationProgramBase])
async def get_all_programs(db: Session = Depends(get_db)):
    """Получение списка программ с привязанными дисциплинами"""
    try:
        # Фильтруем программы, у которых есть хотя бы одна дисциплина
        programs = (
            db.query(EducationProgram)
            .join(Curriculum, EducationProgram.program_id == Curriculum.program_id)
            .group_by(EducationProgram.program_id)
            .having(func.count(Curriculum.curriculum_id) > 0)
            .order_by(EducationProgram.program_name)
            .all()
        )
        
        logger.info(f"Found {len(programs)} active programs")
        return programs
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(500, detail="Ошибка сервера")


# @router.get("/program/{program_id}", response_model=List[CurriculumBase])
# async def get_curriculum_by_program(program_id: int, db: Session = Depends(get_db)):
#     """Получение учебного плана по ID программы"""
#     try:
#         curriculum = (
#             db.query(Curriculum)
#             .options(joinedload(Curriculum.teachers))
#             .order_by(Curriculum.semester, Curriculum.discipline)
#             .all()
#         )

#         if not curriculum:
#             logger.warning(f"No curriculum found for program_id: {program_id}")
#             raise HTTPException(404, detail="Учебный план не найден")

#         logger.info(f"Found {len(curriculum)} disciplines for program {program_id}")
#         return curriculum
#     except Exception as e:
#         logger.error(f"Error fetching curriculum: {str(e)}")
#         raise HTTPException(500, detail="Internal server error")
    
from collections import defaultdict
from typing import Dict, List, Tuple

from sqlalchemy.orm import aliased
from sqlalchemy import func, distinct, and_, select

@router.get("/program/{program_id}", response_model=List[CurriculumBase])
async def get_curriculum_by_program(program_id: int, db: Session = Depends(get_db)):
    """Получение учебного плана с учетом дисциплин без преподавателей"""
    try:
        # Шаг 1: Получаем все дисциплины учебного плана
        curriculum_items = (
            db.query(Curriculum)
            .filter(Curriculum.program_id == program_id)
            .order_by(Curriculum.curriculum_id)
            .all()
        )

        if not curriculum_items:
            logger.warning(f"No curriculum found for program_id: {program_id}")
            raise HTTPException(404, detail="Учебный план не найден")

        # Шаг 2: Получаем всех преподавателей для этих дисциплин
        curriculum_ids = [item.curriculum_id for item in curriculum_items]
        taught_disciplines = (
            db.query(TaughtDiscipline)
            .filter(TaughtDiscipline.curriculum_id.in_(curriculum_ids))
            .options(joinedload(TaughtDiscipline.teacher))
            .all()
        )

        # Шаг 3: Создаем маппинг curriculum_id -> список преподавателей
        teachers_map = defaultdict(list)
        for td in taught_disciplines:
            teachers_map[td.curriculum_id].append(td.teacher)

        # Шаг 4: Формируем результат
        result = []
        for item in curriculum_items:
            # Определяем семестр
            semester = item.semester[0] if item.semester and isinstance(item.semester, list) else item.semester
            
            # Получаем преподавателей для этой дисциплины
            teachers = teachers_map.get(item.curriculum_id, [])
            
            # Создаем объект дисциплины
            curriculum_data = {
                "discipline": item.discipline,
                "department": item.department,
                "semester": semester,
                "lecture_hours": item.lecture_hours or 0,
                "practice_hours": item.practice_hours or 0,
                "lab_hours": item.lab_hours or 0,
                "exam_hours": item.exam_hours or 0,
                "test_hours": item.test_hours or 0,
                "course_project_hours": item.course_project_hours or 0,
                "total_practice_hours": item.total_practice_hours or 0,
                "final_work_hours": item.final_work_hours or 0,
                "teachers": [{
                    "teacher_id": t.teacher_id,
                    "full_name": t.full_name,
                    "position": t.position
                } for t in teachers]
            }
            
            result.append(CurriculumBase(**curriculum_data))

        # Логирование для отладки
        logger.debug(f"Returning {len(result)} curriculum items")
        logger.debug(f"Items without teachers: {sum(1 for item in result if not item.teachers)}")
        
        return result

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(500, detail="Internal server error")

# Временный эндпоинт для проверки сырых данных
@router.get("/debug/program/{program_id}")
async def debug_curriculum(program_id: int, db: Session = Depends(get_db)):
    stmt = db.query(
        Curriculum.discipline,
        Curriculum.department,
        Curriculum.semester,
        func.count(Curriculum.curriculum_id).label("count")
    ).filter(
        Curriculum.program_id == program_id
    ).group_by(
        Curriculum.discipline,
        Curriculum.department,
        Curriculum.semester
    ).having(
        func.count(Curriculum.curriculum_id) > 1
    )
    
    duplicates = stmt.all()
    return {"duplicates": duplicates}